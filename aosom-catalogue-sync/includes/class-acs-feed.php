<?php
/**
 * Feed fetcher + CSV reader.
 *
 * Downloads the feed to a temporary file (streamed, so large feeds don't blow
 * the memory limit) and yields rows as associative arrays keyed by header name.
 *
 * @package AosomCatalogueSync
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class ACS_Feed {

	/**
	 * @var array Settings.
	 */
	private $s;

	/**
	 * @var string Local temp path.
	 */
	private $tmp = '';

	/**
	 * @param array $settings Resolved settings.
	 */
	public function __construct( array $settings ) {
		$this->s = $settings;
	}

	/**
	 * Download the feed to a temp file.
	 *
	 * @return true|WP_Error
	 */
	public function download() {
		$url = $this->s['feed_url'];
		if ( empty( $url ) || ! wp_http_validate_url( $url ) ) {
			return new WP_Error( 'acs_bad_url', __( 'The feed URL is empty or invalid.', 'aosom-catalogue-sync' ) );
		}

		require_once ABSPATH . 'wp-admin/includes/file.php';

		$tmp = download_url( $url, 300 );
		if ( is_wp_error( $tmp ) ) {
			return $tmp;
		}
		$this->tmp = $tmp;
		return true;
	}

	/**
	 * Read the header row of the already-downloaded feed.
	 *
	 * @return array|WP_Error List of column names.
	 */
	public function header() {
		if ( empty( $this->tmp ) || ! is_readable( $this->tmp ) ) {
			return new WP_Error( 'acs_no_file', __( 'Feed has not been downloaded.', 'aosom-catalogue-sync' ) );
		}
		$fh = fopen( $this->tmp, 'rb' );
		if ( ! $fh ) {
			return new WP_Error( 'acs_open', __( 'Could not open the downloaded feed.', 'aosom-catalogue-sync' ) );
		}
		$row = fgetcsv( $fh, 0, $this->s['feed_delimiter'], $this->s['feed_enclosure'] );
		fclose( $fh );
		if ( false === $row ) {
			return new WP_Error( 'acs_empty', __( 'The feed appears to be empty.', 'aosom-catalogue-sync' ) );
		}
		return array_map( 'trim', $row );
	}

	/**
	 * Generator yielding each data row as an associative array.
	 * Skips the header when has_header is on; otherwise yields numeric keys.
	 *
	 * @return \Generator|WP_Error
	 */
	public function rows() {
		if ( empty( $this->tmp ) || ! is_readable( $this->tmp ) ) {
			return new WP_Error( 'acs_no_file', __( 'Feed has not been downloaded.', 'aosom-catalogue-sync' ) );
		}
		$fh = fopen( $this->tmp, 'rb' );
		if ( ! $fh ) {
			return new WP_Error( 'acs_open', __( 'Could not open the downloaded feed.', 'aosom-catalogue-sync' ) );
		}

		$delim  = $this->s['feed_delimiter'];
		$encl   = $this->s['feed_enclosure'];
		$header = null;

		if ( ! empty( $this->s['has_header'] ) ) {
			$header = fgetcsv( $fh, 0, $delim, $encl );
			if ( is_array( $header ) ) {
				$header = array_map( 'trim', $header );
			}
		}

		while ( false !== ( $data = fgetcsv( $fh, 0, $delim, $encl ) ) ) {
			if ( null === $data || array( null ) === $data ) {
				continue; // blank line
			}
			if ( $header ) {
				// Pad/truncate to header length to avoid combine warnings.
				$count = count( $header );
				$data  = array_pad( array_slice( $data, 0, $count ), $count, '' );
				yield array_combine( $header, $data );
			} else {
				yield $data;
			}
		}
		fclose( $fh );
	}

	/**
	 * Remove the temp file.
	 */
	public function cleanup() {
		if ( $this->tmp && file_exists( $this->tmp ) ) {
			@unlink( $this->tmp );
		}
		$this->tmp = '';
	}
}
