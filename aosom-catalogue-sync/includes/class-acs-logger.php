<?php
/**
 * Simple run logger. Writes a timestamped log file per run into the uploads
 * directory and keeps a short summary of the most recent run in an option so
 * the admin screen can show it quickly.
 *
 * @package AosomCatalogueSync
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class ACS_Logger {

	const SUMMARY_OPTION = 'acs_last_run';

	/**
	 * @var string Absolute path to the active log file.
	 */
	private $file = '';

	/**
	 * @var resource|null
	 */
	private $handle = null;

	/**
	 * @var array Counters for the summary.
	 */
	private $counters = array(
		'created'   => 0,
		'updated'   => 0,
		'skipped'   => 0,
		'errors'    => 0,
		'processed' => 0,
	);

	/**
	 * @var bool Whether this run is a dry-run.
	 */
	private $dry = false;

	/**
	 * @var array Rows captured for the preview table (dry-run only).
	 */
	private $preview = array();

	/**
	 * Ensure the log directory exists and is protected.
	 */
	public static function install() {
		$dir = self::log_dir();
		if ( ! is_dir( $dir ) ) {
			wp_mkdir_p( $dir );
		}
		// Block directory listing / direct access to logs.
		$index = $dir . '/index.php';
		if ( ! file_exists( $index ) ) {
			@file_put_contents( $index, "<?php // Silence is golden.\n" );
		}
		$ht = $dir . '/.htaccess';
		if ( ! file_exists( $ht ) ) {
			@file_put_contents( $ht, "Require all denied\nDeny from all\n" );
		}
	}

	/**
	 * @return string Log directory path.
	 */
	public static function log_dir() {
		$uploads = wp_upload_dir();
		return trailingslashit( $uploads['basedir'] ) . 'acs-logs';
	}

	/**
	 * Start a new run log.
	 *
	 * @param bool $dry Dry-run flag.
	 */
	public function start( $dry = false ) {
		$this->dry = (bool) $dry;
		self::install();
		$name       = gmdate( 'Y-m-d_His' ) . ( $dry ? '_dryrun' : '' ) . '.log';
		$this->file = trailingslashit( self::log_dir() ) . $name;
		$this->handle = @fopen( $this->file, 'ab' );
		$this->line( sprintf( '=== %s started %s UTC ===', $dry ? 'DRY-RUN' : 'SYNC', gmdate( 'Y-m-d H:i:s' ) ) );
	}

	/**
	 * Write a line to the log.
	 *
	 * @param string $message Message.
	 */
	public function line( $message ) {
		if ( $this->handle ) {
			@fwrite( $this->handle, '[' . gmdate( 'H:i:s' ) . '] ' . $message . "\n" );
		}
	}

	/**
	 * Record a per-product result.
	 *
	 * @param string $sku    SKU.
	 * @param string $action created|updated|skipped|error.
	 * @param string $detail Detail text.
	 * @param array  $extra  Optional preview fields (price, cost, title...).
	 */
	public function record( $sku, $action, $detail = '', $extra = array() ) {
		$this->counters['processed']++;
		if ( isset( $this->counters[ $action ] ) ) {
			$this->counters[ $action ]++;
		}
		$this->line( sprintf( '%-8s %-24s %s', strtoupper( $action ), $sku, $detail ) );

		if ( $this->dry && count( $this->preview ) < 500 ) {
			$this->preview[] = array_merge(
				array(
					'sku'    => $sku,
					'action' => $action,
					'detail' => $detail,
				),
				$extra
			);
		}
	}

	/**
	 * Finish the run and persist the summary.
	 *
	 * @return array Summary.
	 */
	public function finish() {
		$this->line( sprintf(
			'=== finished: processed %d, created %d, updated %d, skipped %d, errors %d ===',
			$this->counters['processed'],
			$this->counters['created'],
			$this->counters['updated'],
			$this->counters['skipped'],
			$this->counters['errors']
		) );
		if ( $this->handle ) {
			@fclose( $this->handle );
			$this->handle = null;
		}

		$summary = array(
			'time'     => time(),
			'dry'      => $this->dry,
			'file'     => basename( $this->file ),
			'counters' => $this->counters,
			'preview'  => $this->preview,
		);
		update_option( self::SUMMARY_OPTION, $summary, false );
		return $summary;
	}

	/**
	 * @return array Current counters.
	 */
	public function counters() {
		return $this->counters;
	}

	/**
	 * Fetch the stored summary of the last run.
	 *
	 * @return array|null
	 */
	public static function last_run() {
		$s = get_option( self::SUMMARY_OPTION );
		return is_array( $s ) ? $s : null;
	}
}
