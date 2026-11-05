<?php
/**
 * Plugin Name:       Aosom & CSV Catalogue Sync for WooCommerce
 * Plugin URI:        https://digiadagency.co.uk/
 * Description:        Imports and daily-syncs products from a CSV feed (Aosom UK and any other CSV source) into WooCommerce. Category-flexible, with a configurable, preview-able pricing engine that bakes delivery into the price so you never sell below cost.
 * Version:           0.1.0
 * Requires at least: 6.0
 * Requires PHP:      7.4
 * Author:            Digiad Agency
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       aosom-catalogue-sync
 * Domain Path:       /languages
 * WC requires at least: 7.0
 * WC tested up to:   9.3
 *
 * @package AosomCatalogueSync
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // No direct access.
}

define( 'ACS_VERSION', '0.1.0' );
define( 'ACS_PLUGIN_FILE', __FILE__ );
define( 'ACS_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );
define( 'ACS_PLUGIN_URL', plugin_dir_url( __FILE__ ) );
define( 'ACS_PLUGIN_BASENAME', plugin_basename( __FILE__ ) );

// Option + hook names kept in one place.
define( 'ACS_OPTION_SETTINGS', 'acs_settings' );
define( 'ACS_CRON_HOOK', 'acs_scheduled_sync' );

/**
 * Autoloader for ACS_* classes in /includes.
 */
spl_autoload_register(
	static function ( $class ) {
		if ( strpos( $class, 'ACS_' ) !== 0 ) {
			return;
		}
		$slug = strtolower( str_replace( '_', '-', substr( $class, 4 ) ) );
		$file = ACS_PLUGIN_DIR . 'includes/class-acs-' . $slug . '.php';
		if ( is_readable( $file ) ) {
			require_once $file;
		}
	}
);

/**
 * Declare compatibility with WooCommerce High-Performance Order Storage (HPOS).
 */
add_action(
	'before_woocommerce_init',
	static function () {
		if ( class_exists( \Automattic\WooCommerce\Utilities\FeaturesUtil::class ) ) {
			\Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility( 'custom_order_tables', ACS_PLUGIN_FILE, true );
		}
	}
);

/**
 * Boot the plugin once all plugins are loaded, and only if WooCommerce is active.
 */
add_action(
	'plugins_loaded',
	static function () {
		load_plugin_textdomain( 'aosom-catalogue-sync', false, dirname( ACS_PLUGIN_BASENAME ) . '/languages' );

		if ( ! class_exists( 'WooCommerce' ) ) {
			add_action(
				'admin_notices',
				static function () {
					echo '<div class="notice notice-error"><p>';
					echo esc_html__( 'Aosom & CSV Catalogue Sync requires WooCommerce to be installed and active.', 'aosom-catalogue-sync' );
					echo '</p></div>';
				}
			);
			return;
		}

		ACS_Plugin::instance()->init();
	}
);

// Activation / deactivation.
register_activation_hook(
	__FILE__,
	static function () {
		require_once ACS_PLUGIN_DIR . 'includes/class-acs-logger.php';
		ACS_Logger::install();
		// Schedule is (re)created from settings when the user saves; nothing to force here.
	}
);

register_deactivation_hook(
	__FILE__,
	static function () {
		$timestamp = wp_next_scheduled( ACS_CRON_HOOK );
		if ( $timestamp ) {
			wp_unschedule_event( $timestamp, ACS_CRON_HOOK );
		}
		wp_clear_scheduled_hook( ACS_CRON_HOOK );
	}
);
