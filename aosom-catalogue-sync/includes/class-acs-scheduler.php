<?php
/**
 * Daily schedule via WP-Cron. For high-traffic stores, point a real server
 * cron at wp-cron.php (or use WP-CLI `wp acs sync`) and disable WP pseudo-cron.
 *
 * @package AosomCatalogueSync
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class ACS_Scheduler {

	/**
	 * @var ACS_Settings
	 */
	private $settings;

	public function __construct( ACS_Settings $settings ) {
		$this->settings = $settings;
	}

	public function init() {
		add_action( ACS_CRON_HOOK, array( $this, 'run' ) );
		add_action( 'update_option_' . ACS_OPTION_SETTINGS, array( $this, 'reschedule' ), 10, 0 );
		$this->ensure_scheduled();
	}

	/**
	 * Make sure the event matches current settings.
	 */
	public function ensure_scheduled() {
		$enabled = (int) $this->settings->value( 'schedule_enabled', 0 );
		$next    = wp_next_scheduled( ACS_CRON_HOOK );

		if ( ! $enabled ) {
			if ( $next ) {
				wp_unschedule_event( $next, ACS_CRON_HOOK );
			}
			return;
		}

		if ( ! $next ) {
			wp_schedule_event( $this->next_run_timestamp(), 'daily', ACS_CRON_HOOK );
		}
	}

	/**
	 * Re-apply scheduling after settings save.
	 */
	public function reschedule() {
		$this->settings = new ACS_Settings(); // bust cache
		$next = wp_next_scheduled( ACS_CRON_HOOK );
		if ( $next ) {
			wp_unschedule_event( $next, ACS_CRON_HOOK );
		}
		if ( (int) $this->settings->value( 'schedule_enabled', 0 ) ) {
			wp_schedule_event( $this->next_run_timestamp(), 'daily', ACS_CRON_HOOK );
		}
	}

	/**
	 * Next occurrence of the configured HH:MM in site timezone, as a UTC timestamp.
	 *
	 * @return int
	 */
	private function next_run_timestamp() {
		$time = (string) $this->settings->value( 'schedule_time', '03:00' );
		list( $h, $m ) = array_map( 'intval', explode( ':', $time . ':0' ) );

		$tz  = wp_timezone();
		$now = new DateTime( 'now', $tz );
		$run = new DateTime( 'now', $tz );
		$run->setTime( $h, $m, 0 );
		if ( $run <= $now ) {
			$run->modify( '+1 day' );
		}
		return $run->getTimestamp();
	}

	/**
	 * Cron callback: run a real (non-dry) sync.
	 */
	public function run() {
		$importer = new ACS_Importer( $this->settings->get() );
		$importer->run( false );
	}
}
