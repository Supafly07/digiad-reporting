<?php
/**
 * Settings store + defaults + sanitisation.
 *
 * All configuration lives in a single option (ACS_OPTION_SETTINGS) so the
 * plugin is self-contained and easy to export between stores.
 *
 * @package AosomCatalogueSync
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class ACS_Settings {

	/**
	 * Cached settings.
	 *
	 * @var array|null
	 */
	private $cache = null;

	/**
	 * Default settings. These are intentionally conservative:
	 * - price source is the REGULAR price (never the discount column)
	 * - delivery is baked into the price (product + shipping)
	 * - a row with a missing/zero price is skipped, never published
	 *
	 * The Aosom column names below are placeholders to be confirmed against
	 * the live feed header; everything is remappable in the admin screen.
	 *
	 * @return array
	 */
	public static function defaults() {
		return array(
			// --- Feed source ---
			'feed_url'            => 'https://feed.aosomcdn.com/390/200_feed/0/0/14a/c4857d.csv',
			'feed_delimiter'      => ',',
			'feed_enclosure'      => '"',
			'has_header'          => 1,

			// --- Column mapping (CSV header name -> WooCommerce field) ---
			// Confirm these names against the real feed header before go-live.
			'map_sku'             => 'SKU',
			'map_title'           => 'Title',
			'map_description'     => 'Description',
			'map_regular_price'   => 'Price',          // regular product price, inc VAT, excl shipping
			'map_shipping_price'  => 'Shipping',       // shipping price, inc VAT
			'map_discount_price'  => 'Discount Price', // promo price - NOT used for selling price by default
			'map_stock'           => 'Stock',
			'map_category'        => 'Category',
			'map_brand'           => 'Brand',
			'map_ean'             => 'EAN',
			'map_image'           => 'Image URL',      // primary image
			'map_images_extra'    => 'Additional Images', // pipe/comma separated gallery (optional)
			'map_weight'          => 'Weight',
			'map_url'             => 'Product URL',     // source URL (stored as meta for manual fulfilment)

			// --- Pricing engine ---
			'price_source'        => 'regular',        // regular | discount  (regular strongly recommended)
			'base_mode'           => 'product_plus_shipping', // product_plus_shipping | product_only
			'markup_percent'      => 10.0,
			'handling_fee'        => 0.0,              // flat amount added after markup
			'rounding'            => 'charm_99',       // none | charm_99 | charm_95 | nearest_1 | nearest_050
			'price_includes_tax'  => 1,                // feed prices already include VAT
			'min_margin_percent'  => 0.0,              // extra safety margin over cost before publishing

			// --- Category filtering & mapping (makes the plugin reusable across stores) ---
			// Only import rows whose source category matches one of these (comma separated, case-insensitive substring). Empty = import everything in the feed.
			'filter_categories'   => 'pet',
			'filter_sku_prefix'   => '',               // optional comma separated SKU prefixes
			'filter_keywords'     => '',               // optional comma separated title keywords
			// Map a matched source category to a WooCommerce category. One rule per line: "source => Woo Category".
			'category_map'        => "pet => Pet Supplies",
			'default_category'    => 'Pet Supplies',   // fallback Woo category when no rule matches

			// --- Product behaviour ---
			'publish_status'      => 'publish',        // publish | draft
			'missing_price_action'=> 'skip',           // skip | draft  (never publish a priced-wrong product)
			'out_of_stock_action' => 'outofstock',     // outofstock | draft | keep
			'manage_stock'        => 1,
			'import_images'       => 1,
			'update_existing'     => 1,
			'remove_absent'       => 'none',           // none | draft | outofstock  (what to do with products no longer in the feed)

			// --- Schedule ---
			'schedule_enabled'    => 0,
			'schedule_time'       => '03:00',          // HH:MM site time
			'batch_size'          => 50,               // products per cron chunk

			// --- Safety ---
			'dry_run_default'     => 1,                 // preview before first real run
		);
	}

	/**
	 * Get merged settings (saved over defaults).
	 *
	 * @return array
	 */
	public function get() {
		if ( null !== $this->cache ) {
			return $this->cache;
		}
		$saved       = get_option( ACS_OPTION_SETTINGS, array() );
		$this->cache = wp_parse_args( is_array( $saved ) ? $saved : array(), self::defaults() );
		return $this->cache;
	}

	/**
	 * Single value helper.
	 *
	 * @param string $key     Setting key.
	 * @param mixed  $default Fallback.
	 * @return mixed
	 */
	public function value( $key, $default = null ) {
		$all = $this->get();
		return array_key_exists( $key, $all ) ? $all[ $key ] : $default;
	}

	/**
	 * Save raw $_POST-style input, sanitised.
	 *
	 * @param array $input Raw input.
	 * @return array Saved settings.
	 */
	public function save( array $input ) {
		$clean    = $this->sanitize( $input );
		$this->cache = null;
		update_option( ACS_OPTION_SETTINGS, $clean );
		return $this->get();
	}

	/**
	 * Sanitise all known settings.
	 *
	 * @param array $input Raw.
	 * @return array
	 */
	public function sanitize( array $input ) {
		$d   = self::defaults();
		$out = array();

		$text_keys = array(
			'feed_delimiter', 'feed_enclosure',
			'map_sku', 'map_title', 'map_description', 'map_regular_price', 'map_shipping_price',
			'map_discount_price', 'map_stock', 'map_category', 'map_brand', 'map_ean', 'map_image',
			'map_images_extra', 'map_weight', 'map_url',
			'filter_categories', 'filter_sku_prefix', 'filter_keywords', 'default_category', 'schedule_time',
		);
		foreach ( $text_keys as $k ) {
			$out[ $k ] = isset( $input[ $k ] ) ? sanitize_text_field( wp_unslash( $input[ $k ] ) ) : $d[ $k ];
		}

		$out['feed_url']    = isset( $input['feed_url'] ) ? esc_url_raw( wp_unslash( $input['feed_url'] ) ) : $d['feed_url'];
		$out['category_map'] = isset( $input['category_map'] ) ? sanitize_textarea_field( wp_unslash( $input['category_map'] ) ) : $d['category_map'];

		// Floats.
		foreach ( array( 'markup_percent', 'handling_fee', 'min_margin_percent' ) as $k ) {
			$out[ $k ] = isset( $input[ $k ] ) ? max( 0, (float) $input[ $k ] ) : $d[ $k ];
		}

		// Ints / booleans.
		foreach ( array( 'has_header', 'price_includes_tax', 'manage_stock', 'import_images', 'update_existing', 'schedule_enabled', 'dry_run_default' ) as $k ) {
			$out[ $k ] = empty( $input[ $k ] ) ? 0 : 1;
		}
		$out['batch_size'] = isset( $input['batch_size'] ) ? max( 1, min( 500, (int) $input['batch_size'] ) ) : $d['batch_size'];

		// Enums.
		$out['price_source']         = in_array( $input['price_source'] ?? '', array( 'regular', 'discount' ), true ) ? $input['price_source'] : $d['price_source'];
		$out['base_mode']            = in_array( $input['base_mode'] ?? '', array( 'product_plus_shipping', 'product_only' ), true ) ? $input['base_mode'] : $d['base_mode'];
		$out['rounding']             = in_array( $input['rounding'] ?? '', array( 'none', 'charm_99', 'charm_95', 'nearest_1', 'nearest_050' ), true ) ? $input['rounding'] : $d['rounding'];
		$out['publish_status']       = in_array( $input['publish_status'] ?? '', array( 'publish', 'draft' ), true ) ? $input['publish_status'] : $d['publish_status'];
		$out['missing_price_action'] = in_array( $input['missing_price_action'] ?? '', array( 'skip', 'draft' ), true ) ? $input['missing_price_action'] : $d['missing_price_action'];
		$out['out_of_stock_action']  = in_array( $input['out_of_stock_action'] ?? '', array( 'outofstock', 'draft', 'keep' ), true ) ? $input['out_of_stock_action'] : $d['out_of_stock_action'];
		$out['remove_absent']        = in_array( $input['remove_absent'] ?? '', array( 'none', 'draft', 'outofstock' ), true ) ? $input['remove_absent'] : $d['remove_absent'];

		// HH:MM validation.
		if ( ! preg_match( '/^([01]\d|2[0-3]):[0-5]\d$/', $out['schedule_time'] ) ) {
			$out['schedule_time'] = $d['schedule_time'];
		}

		return $out;
	}

	/**
	 * Parse the "source => Woo Category" map into an associative array.
	 *
	 * @return array<string,string>
	 */
	public function category_map() {
		$raw   = (string) $this->value( 'category_map', '' );
		$map   = array();
		$lines = preg_split( '/\r\n|\r|\n/', $raw );
		foreach ( $lines as $line ) {
			$line = trim( $line );
			if ( '' === $line || false === strpos( $line, '=>' ) ) {
				continue;
			}
			list( $src, $dest ) = array_map( 'trim', explode( '=>', $line, 2 ) );
			if ( '' !== $src && '' !== $dest ) {
				$map[ mb_strtolower( $src ) ] = $dest;
			}
		}
		return $map;
	}

	/**
	 * Comma-separated setting -> trimmed array (lower-cased).
	 *
	 * @param string $key Setting key.
	 * @return string[]
	 */
	public function csv_list( $key ) {
		$raw = (string) $this->value( $key, '' );
		if ( '' === trim( $raw ) ) {
			return array();
		}
		return array_values( array_filter( array_map(
			static function ( $v ) {
				return mb_strtolower( trim( $v ) );
			},
			explode( ',', $raw )
		) ) );
	}
}
