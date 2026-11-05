<?php
/**
 * Main plugin controller: wires together admin, scheduler and settings.
 *
 * @package AosomCatalogueSync
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class ACS_Plugin {

	/**
	 * @var ACS_Plugin|null
	 */
	private static $instance = null;

	/**
	 * @var ACS_Settings
	 */
	private $settings;

	/**
	 * @var ACS_Admin
	 */
	private $admin;

	/**
	 * @var ACS_Scheduler
	 */
	private $scheduler;

	public static function instance() {
		if ( null === self::$instance ) {
			self::$instance = new self();
		}
		return self::$instance;
	}

	private function __construct() {}

	/**
	 * Hook everything up.
	 */
	public function init() {
		$this->settings  = new ACS_Settings();
		$this->scheduler = new ACS_Scheduler( $this->settings );
		$this->scheduler->init();

		if ( is_admin() ) {
			$this->admin = new ACS_Admin( $this->settings );
			$this->admin->init();
		}

		// WP-CLI command for running a sync from the command line / real cron.
		if ( defined( 'WP_CLI' ) && WP_CLI ) {
			\WP_CLI::add_command(
				'acs sync',
				function ( $args, $assoc_args ) {
					$dry = isset( $assoc_args['dry-run'] );
					$importer = new ACS_Importer( $this->settings->get() );
					$result   = $importer->run( $dry );
					\WP_CLI::success( sprintf( '%s complete. Created %d, updated %d, skipped %d.', $dry ? 'Dry-run' : 'Sync', $result['created'], $result['updated'], $result['skipped'] ) );
				}
			);
		}
	}

	/**
	 * @return ACS_Settings
	 */
	public function settings() {
		return $this->settings;
	}
}
