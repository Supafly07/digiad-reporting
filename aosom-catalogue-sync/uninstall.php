<?php
/**
 * Uninstall cleanup. Removes plugin options and scheduled events.
 * Imported products are intentionally left in place.
 *
 * @package AosomCatalogueSync
 */

if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
	exit;
}

delete_option( 'acs_settings' );
delete_option( 'acs_last_run' );

$timestamp = wp_next_scheduled( 'acs_scheduled_sync' );
if ( $timestamp ) {
	wp_unschedule_event( $timestamp, 'acs_scheduled_sync' );
}
wp_clear_scheduled_hook( 'acs_scheduled_sync' );
