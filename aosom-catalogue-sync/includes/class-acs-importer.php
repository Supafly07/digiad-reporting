<?php
/**
 * Import engine: feed -> filter -> price -> WooCommerce product upsert.
 *
 * @package AosomCatalogueSync
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class ACS_Importer {

	/**
	 * @var array Settings.
	 */
	private $s;

	/**
	 * @var ACS_Pricing
	 */
	private $pricing;

	/**
	 * @var ACS_Logger
	 */
	private $log;

	/**
	 * @var ACS_Settings
	 */
	private $settings_obj;

	/**
	 * @param array $settings Resolved settings array.
	 */
	public function __construct( array $settings ) {
		$this->s            = $settings;
		$this->pricing      = new ACS_Pricing( $settings );
		$this->log          = new ACS_Logger();
		$this->settings_obj = new ACS_Settings();
	}

	/**
	 * Run a full sync.
	 *
	 * @param bool $dry      Dry-run (compute + preview, write nothing).
	 * @param int  $max_rows Optional cap (0 = all). Used by the preview button.
	 * @return array Summary with counters (+ preview rows in dry-run).
	 */
	public function run( $dry = false, $max_rows = 0 ) {
		@set_time_limit( 0 );
		$this->log->start( $dry );

		$feed = new ACS_Feed( $this->s );
		$dl   = $feed->download();
		if ( is_wp_error( $dl ) ) {
			$this->log->line( 'ERROR downloading feed: ' . $dl->get_error_message() );
			$this->log->record( '-', 'error', $dl->get_error_message() );
			return $this->log->finish();
		}

		$cat_map         = $this->settings_obj->category_map();
		$filter_cats     = $this->settings_obj->csv_list( 'filter_categories' );
		$filter_prefixes = $this->settings_obj->csv_list( 'filter_sku_prefix' );
		$filter_keywords = $this->settings_obj->csv_list( 'filter_keywords' );

		$seen = array();
		$n    = 0;

		$rows = $feed->rows();
		if ( is_wp_error( $rows ) ) {
			$this->log->record( '-', 'error', $rows->get_error_message() );
			$feed->cleanup();
			return $this->log->finish();
		}

		foreach ( $rows as $row ) {
			if ( $max_rows && $n >= $max_rows ) {
				break;
			}
			$n++;

			$sku = $this->col( $row, 'map_sku' );
			if ( '' === $sku ) {
				$this->log->record( '(no sku)', 'skipped', __( 'Row has no SKU.', 'aosom-catalogue-sync' ) );
				continue;
			}

			$title    = $this->col( $row, 'map_title' );
			$source_cat = $this->col( $row, 'map_category' );

			// --- Filters (make the plugin category-flexible / reusable) ---
			if ( ! $this->passes_filters( $sku, $title, $source_cat, $filter_cats, $filter_prefixes, $filter_keywords ) ) {
				continue; // silently out of scope for this store
			}

			// --- Pricing ---
			$price_result = $this->pricing->compute(
				$this->col( $row, 'map_regular_price' ),
				$this->col( $row, 'map_shipping_price' ),
				$this->col( $row, 'map_discount_price' )
			);

			$extra = array(
				'title' => $title,
				'price' => $price_result['price'],
				'cost'  => $price_result['cost'],
			);

			if ( ! $price_result['ok'] ) {
				if ( 'draft' === $this->s['missing_price_action'] && ! $dry ) {
					$this->upsert( $row, $sku, $title, $source_cat, $cat_map, 0.0, true /* force draft */ );
				}
				$this->log->record( $sku, 'skipped', $price_result['reason'], $extra );
				$seen[ $sku ] = true;
				continue;
			}

			if ( $dry ) {
				$existing = $this->find_by_sku( $sku );
				$this->log->record(
					$sku,
					$existing ? 'updated' : 'created',
					sprintf( 'price %s (cost %s)', number_format( $price_result['price'], 2 ), number_format( $price_result['cost'], 2 ) ),
					$extra
				);
				$seen[ $sku ] = true;
				continue;
			}

			$this->upsert( $row, $sku, $title, $source_cat, $cat_map, $price_result['price'], false );
			$seen[ $sku ] = true;
		}

		$feed->cleanup();

		// Handle products that are no longer in the feed.
		if ( ! $dry && 'none' !== $this->s['remove_absent'] && ! $max_rows ) {
			$this->handle_absent( $seen );
		}

		return $this->log->finish();
	}

	/**
	 * Filter check.
	 */
	private function passes_filters( $sku, $title, $source_cat, $cats, $prefixes, $keywords ) {
		if ( ! empty( $cats ) ) {
			$hay = mb_strtolower( $source_cat );
			$hit = false;
			foreach ( $cats as $c ) {
				if ( '' !== $c && false !== mb_strpos( $hay, $c ) ) {
					$hit = true;
					break;
				}
			}
			if ( ! $hit ) {
				return false;
			}
		}
		if ( ! empty( $prefixes ) ) {
			$hit = false;
			foreach ( $prefixes as $p ) {
				if ( '' !== $p && 0 === mb_stripos( $sku, $p ) ) {
					$hit = true;
					break;
				}
			}
			if ( ! $hit ) {
				return false;
			}
		}
		if ( ! empty( $keywords ) ) {
			$hay = mb_strtolower( $title );
			$hit = false;
			foreach ( $keywords as $k ) {
				if ( '' !== $k && false !== mb_strpos( $hay, $k ) ) {
					$hit = true;
					break;
				}
			}
			if ( ! $hit ) {
				return false;
			}
		}
		return true;
	}

	/**
	 * Create or update a WooCommerce product from a feed row.
	 */
	private function upsert( $row, $sku, $title, $source_cat, $cat_map, $price, $force_draft ) {
		$product = $this->find_by_sku( $sku );
		$is_new  = false;

		if ( ! $product ) {
			if ( ! $this->s['update_existing'] && false ) {
				// placeholder: update_existing only affects existing products
			}
			$product = new WC_Product_Simple();
			$product->set_sku( $sku );
			$is_new = true;
		} elseif ( ! $this->s['update_existing'] ) {
			$this->log->record( $sku, 'skipped', __( 'Exists and "update existing" is off.', 'aosom-catalogue-sync' ) );
			return;
		}

		if ( '' !== $title ) {
			$product->set_name( $title );
		}
		$desc = $this->col( $row, 'map_description' );
		if ( '' !== $desc ) {
			$product->set_description( wp_kses_post( $desc ) );
		}

		if ( $price > 0 ) {
			$product->set_regular_price( (string) $price );
			$product->set_price( (string) $price );
		}

		// Stock.
		$stock_raw = $this->col( $row, 'map_stock' );
		$this->apply_stock( $product, $stock_raw );

		// Category.
		$term_id = $this->resolve_category( $source_cat, $cat_map );
		if ( $term_id ) {
			$product->set_category_ids( array( $term_id ) );
		}

		// Status: only set on NEW products. Never flip an existing product's
		// published/draft state on a routine sync — the merchant controls that.
		if ( $force_draft ) {
			$product->set_status( 'draft' );
		} elseif ( $is_new ) {
			$product->set_status( $this->s['publish_status'] );
		}
		// Out-of-stock draft policy applies to new and existing alike.
		if ( ! $force_draft && 'draft' === $this->s['out_of_stock_action'] && 'outofstock' === $product->get_stock_status() ) {
			$product->set_status( 'draft' );
		}

		// Meta for manual fulfilment / traceability.
		$product->update_meta_data( '_acs_source', 'aosom' );
		$product->update_meta_data( '_acs_synced', gmdate( 'c' ) );
		$url = $this->col( $row, 'map_url' );
		if ( '' !== $url ) {
			$product->update_meta_data( '_acs_source_url', esc_url_raw( $url ) );
		}
		$brand = $this->col( $row, 'map_brand' );
		if ( '' !== $brand ) {
			$product->update_meta_data( '_acs_brand', $brand );
		}
		$ean = $this->col( $row, 'map_ean' );
		if ( '' !== $ean ) {
			$product->update_meta_data( '_acs_ean', $ean );
			if ( function_exists( 'wc_get_product' ) && method_exists( $product, 'set_global_unique_id' ) ) {
				$product->set_global_unique_id( preg_replace( '/[^0-9]/', '', $ean ) );
			}
		}
		$weight = $this->pricing->to_float( $this->col( $row, 'map_weight' ) );
		if ( $weight > 0 ) {
			$product->set_weight( (string) $weight );
		}

		$product_id = $product->save();

		if ( ! $product_id ) {
			$this->log->record( $sku, 'error', __( 'Product save failed.', 'aosom-catalogue-sync' ) );
			return;
		}

		// Images (after save so we have an ID).
		if ( $this->s['import_images'] ) {
			$this->maybe_import_images( $product_id, $row );
		}

		$this->log->record(
			$sku,
			$is_new ? 'created' : 'updated',
			sprintf( 'id %d, price %s', $product_id, number_format( (float) $price, 2 ) ),
			array( 'title' => $title, 'price' => $price )
		);
	}

	/**
	 * Apply stock quantity / status.
	 */
	private function apply_stock( $product, $stock_raw ) {
		$stock_raw = trim( (string) $stock_raw );

		// Interpret common textual stock values.
		$in_stock = true;
		$qty      = null;
		if ( is_numeric( $stock_raw ) ) {
			$qty      = (int) $stock_raw;
			$in_stock = $qty > 0;
		} elseif ( '' !== $stock_raw ) {
			$lc       = strtolower( $stock_raw );
			$in_stock = ! in_array( $lc, array( 'out of stock', 'outofstock', 'no', '0', 'false', 'unavailable' ), true );
		}

		if ( $this->s['manage_stock'] && null !== $qty ) {
			$product->set_manage_stock( true );
			$product->set_stock_quantity( max( 0, $qty ) );
			$product->set_stock_status( $qty > 0 ? 'instock' : 'outofstock' );
		} else {
			$product->set_manage_stock( false );
			$product->set_stock_status( $in_stock ? 'instock' : 'outofstock' );
		}

		if ( ! $in_stock && 'outofstock' === $this->s['out_of_stock_action'] ) {
			$product->set_stock_status( 'outofstock' );
		}
	}

	/**
	 * Resolve (creating if necessary) the target Woo product category term ID.
	 */
	private function resolve_category( $source_cat, $cat_map ) {
		$name = $this->s['default_category'];
		$lc   = mb_strtolower( trim( (string) $source_cat ) );

		foreach ( $cat_map as $src => $dest ) {
			if ( '' !== $src && false !== mb_strpos( $lc, $src ) ) {
				$name = $dest;
				break;
			}
		}
		if ( '' === trim( (string) $name ) ) {
			return 0;
		}

		$term = get_term_by( 'name', $name, 'product_cat' );
		if ( $term ) {
			return (int) $term->term_id;
		}
		$created = wp_insert_term( $name, 'product_cat' );
		if ( is_wp_error( $created ) ) {
			return 0;
		}
		return (int) $created['term_id'];
	}

	/**
	 * Import featured + gallery images, idempotently (skip if source unchanged).
	 */
	private function maybe_import_images( $product_id, $row ) {
		$primary = trim( (string) $this->col( $row, 'map_image' ) );
		if ( '' === $primary ) {
			return;
		}

		$extra_raw = (string) $this->col( $row, 'map_images_extra' );
		$gallery   = array_filter( array_map( 'trim', preg_split( '/[|,]/', $extra_raw ) ) );

		$signature = md5( $primary . '|' . implode( '|', $gallery ) );
		if ( get_post_meta( $product_id, '_acs_image_sig', true ) === $signature ) {
			return; // unchanged, don't re-download
		}

		require_once ABSPATH . 'wp-admin/includes/media.php';
		require_once ABSPATH . 'wp-admin/includes/file.php';
		require_once ABSPATH . 'wp-admin/includes/image.php';

		$featured_id = $this->sideload( $primary, $product_id );
		if ( $featured_id ) {
			set_post_thumbnail( $product_id, $featured_id );
		}

		$gallery_ids = array();
		foreach ( array_slice( $gallery, 0, 10 ) as $g ) {
			$gid = $this->sideload( $g, $product_id );
			if ( $gid ) {
				$gallery_ids[] = $gid;
			}
		}
		if ( $gallery_ids ) {
			update_post_meta( $product_id, '_product_image_gallery', implode( ',', $gallery_ids ) );
		}

		update_post_meta( $product_id, '_acs_image_sig', $signature );
	}

	/**
	 * Sideload a single image URL, returning the attachment ID (0 on failure).
	 */
	private function sideload( $url, $product_id ) {
		$url = esc_url_raw( $url );
		if ( '' === $url ) {
			return 0;
		}
		$id = media_sideload_image( $url, $product_id, null, 'id' );
		if ( is_wp_error( $id ) ) {
			$this->log->line( 'IMG failed ' . $url . ' : ' . $id->get_error_message() );
			return 0;
		}
		return (int) $id;
	}

	/**
	 * Products present last time but absent from this feed run.
	 */
	private function handle_absent( $seen ) {
		$query = new WP_Query(
			array(
				'post_type'      => 'product',
				'posts_per_page' => -1,
				'fields'         => 'ids',
				'post_status'    => array( 'publish', 'draft' ),
				'meta_key'       => '_acs_source',
				'meta_value'     => 'aosom',
			)
		);
		foreach ( $query->posts as $pid ) {
			$product = wc_get_product( $pid );
			if ( ! $product ) {
				continue;
			}
			$sku = $product->get_sku();
			if ( isset( $seen[ $sku ] ) ) {
				continue;
			}
			if ( 'draft' === $this->s['remove_absent'] ) {
				$product->set_status( 'draft' );
			} else {
				$product->set_stock_status( 'outofstock' );
			}
			$product->save();
			$this->log->record( $sku, 'updated', __( 'Absent from feed: ', 'aosom-catalogue-sync' ) . $this->s['remove_absent'] );
		}
	}

	/**
	 * Find a product by SKU.
	 *
	 * @return WC_Product|null
	 */
	private function find_by_sku( $sku ) {
		$id = wc_get_product_id_by_sku( $sku );
		return $id ? wc_get_product( $id ) : null;
	}

	/**
	 * Read a mapped column value from a row.
	 */
	private function col( $row, $map_key ) {
		$column = $this->s[ $map_key ] ?? '';
		if ( '' === $column ) {
			return '';
		}
		if ( is_array( $row ) && array_key_exists( $column, $row ) ) {
			return trim( (string) $row[ $column ] );
		}
		return '';
	}
}
