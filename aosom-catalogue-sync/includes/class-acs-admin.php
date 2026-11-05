<?php
/**
 * Admin screen: settings form, column detection, dry-run preview, run now, logs.
 *
 * @package AosomCatalogueSync
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class ACS_Admin {

	const CAP  = 'manage_woocommerce';
	const SLUG = 'acs-catalogue-sync';

	/**
	 * @var ACS_Settings
	 */
	private $settings;

	/**
	 * @var array Transient-style notices for this request.
	 */
	private $notices = array();

	public function __construct( ACS_Settings $settings ) {
		$this->settings = $settings;
	}

	public function init() {
		add_action( 'admin_menu', array( $this, 'menu' ) );
		add_action( 'admin_post_acs_save', array( $this, 'handle_save' ) );
		add_action( 'admin_post_acs_test_feed', array( $this, 'handle_test_feed' ) );
		add_action( 'admin_post_acs_dry_run', array( $this, 'handle_dry_run' ) );
		add_action( 'admin_post_acs_run_now', array( $this, 'handle_run_now' ) );
		add_action( 'admin_notices', array( $this, 'maybe_render_transient_notice' ) );
	}

	public function menu() {
		add_submenu_page(
			'woocommerce',
			__( 'Catalogue Sync', 'aosom-catalogue-sync' ),
			__( 'Catalogue Sync', 'aosom-catalogue-sync' ),
			self::CAP,
			self::SLUG,
			array( $this, 'render' )
		);
	}

	/**
	 * Field definitions grouped into sections. Keeps render + mapping DRY.
	 */
	private function fields() {
		return array(
			'Feed source' => array(
				'feed_url'       => array( 'url', __( 'Feed URL', 'aosom-catalogue-sync' ), __( 'The CSV feed address (e.g. the Aosom UK feed).', 'aosom-catalogue-sync' ) ),
				'feed_delimiter' => array( 'text', __( 'Delimiter', 'aosom-catalogue-sync' ), __( 'Usually a comma.', 'aosom-catalogue-sync' ) ),
				'feed_enclosure' => array( 'text', __( 'Enclosure', 'aosom-catalogue-sync' ), __( 'Usually a double quote.', 'aosom-catalogue-sync' ) ),
				'has_header'     => array( 'checkbox', __( 'First row is a header', 'aosom-catalogue-sync' ), '' ),
			),
			'Column mapping' => array(
				'map_sku'            => array( 'text', __( 'SKU column', 'aosom-catalogue-sync' ), __( 'Unique product identifier. Required.', 'aosom-catalogue-sync' ) ),
				'map_title'          => array( 'text', __( 'Title column', 'aosom-catalogue-sync' ), '' ),
				'map_description'    => array( 'text', __( 'Description column', 'aosom-catalogue-sync' ), '' ),
				'map_regular_price'  => array( 'text', __( 'Regular price column', 'aosom-catalogue-sync' ), __( 'The REGULAR product price (inc VAT, excluding shipping).', 'aosom-catalogue-sync' ) ),
				'map_shipping_price' => array( 'text', __( 'Shipping price column', 'aosom-catalogue-sync' ), __( 'Delivery charge (inc VAT). Baked into the sell price by default.', 'aosom-catalogue-sync' ) ),
				'map_discount_price' => array( 'text', __( 'Discount price column', 'aosom-catalogue-sync' ), __( 'Promo price. NOT used for selling price unless you change the pricing source.', 'aosom-catalogue-sync' ) ),
				'map_stock'          => array( 'text', __( 'Stock column', 'aosom-catalogue-sync' ), '' ),
				'map_category'       => array( 'text', __( 'Category column', 'aosom-catalogue-sync' ), '' ),
				'map_brand'          => array( 'text', __( 'Brand column', 'aosom-catalogue-sync' ), '' ),
				'map_ean'            => array( 'text', __( 'EAN/GTIN column', 'aosom-catalogue-sync' ), '' ),
				'map_image'          => array( 'text', __( 'Primary image column', 'aosom-catalogue-sync' ), '' ),
				'map_images_extra'   => array( 'text', __( 'Gallery images column', 'aosom-catalogue-sync' ), __( 'Pipe- or comma-separated extra image URLs.', 'aosom-catalogue-sync' ) ),
				'map_weight'         => array( 'text', __( 'Weight column', 'aosom-catalogue-sync' ), '' ),
				'map_url'            => array( 'text', __( 'Source URL column', 'aosom-catalogue-sync' ), __( 'Stored for manual Aosom ordering.', 'aosom-catalogue-sync' ) ),
			),
			'Pricing' => array(
				'price_source'       => array( 'select', __( 'Price source', 'aosom-catalogue-sync' ), __( 'Use the regular price (recommended) or the discount price.', 'aosom-catalogue-sync' ), array( 'regular' => 'Regular price (recommended)', 'discount' => 'Discount price (not recommended)' ) ),
				'base_mode'          => array( 'select', __( 'Delivery handling', 'aosom-catalogue-sync' ), __( 'Bake delivery into the price, or charge it separately via WooCommerce shipping.', 'aosom-catalogue-sync' ), array( 'product_plus_shipping' => 'Include delivery in price (product + shipping)', 'product_only' => 'Product only (charge delivery separately)' ) ),
				'markup_percent'     => array( 'number', __( 'Markup %', 'aosom-catalogue-sync' ), __( 'Added on top of the base. Policy = 10.', 'aosom-catalogue-sync' ) ),
				'handling_fee'       => array( 'number', __( 'Flat handling fee', 'aosom-catalogue-sync' ), __( 'Optional fixed amount added after markup.', 'aosom-catalogue-sync' ) ),
				'rounding'           => array( 'select', __( 'Rounding', 'aosom-catalogue-sync' ), '', array( 'charm_99' => 'Charm .99', 'charm_95' => 'Charm .95', 'nearest_1' => 'Nearest £1', 'nearest_050' => 'Nearest £0.50', 'none' => 'Exact (2dp)' ) ),
				'min_margin_percent' => array( 'number', __( 'Extra safety margin %', 'aosom-catalogue-sync' ), __( 'Refuse to publish unless the price clears cost by at least this %.', 'aosom-catalogue-sync' ) ),
			),
			'Filtering & categories' => array(
				'filter_categories' => array( 'text', __( 'Only import source categories containing', 'aosom-catalogue-sync' ), __( 'Comma-separated. Empty = import everything. e.g. "pet" for this store.', 'aosom-catalogue-sync' ) ),
				'filter_sku_prefix' => array( 'text', __( 'Only import SKU prefixes', 'aosom-catalogue-sync' ), __( 'Optional, comma-separated.', 'aosom-catalogue-sync' ) ),
				'filter_keywords'   => array( 'text', __( 'Only import titles containing', 'aosom-catalogue-sync' ), __( 'Optional, comma-separated keywords.', 'aosom-catalogue-sync' ) ),
				'category_map'      => array( 'textarea', __( 'Category map', 'aosom-catalogue-sync' ), __( 'One rule per line: source => WooCommerce category.', 'aosom-catalogue-sync' ) ),
				'default_category'  => array( 'text', __( 'Default WooCommerce category', 'aosom-catalogue-sync' ), '' ),
			),
			'Behaviour' => array(
				'publish_status'       => array( 'select', __( 'New product status', 'aosom-catalogue-sync' ), '', array( 'publish' => 'Publish', 'draft' => 'Draft' ) ),
				'missing_price_action' => array( 'select', __( 'If price is invalid', 'aosom-catalogue-sync' ), __( 'Never publish a wrongly-priced product.', 'aosom-catalogue-sync' ), array( 'skip' => 'Skip (leave untouched)', 'draft' => 'Save as draft' ) ),
				'out_of_stock_action'  => array( 'select', __( 'If out of stock', 'aosom-catalogue-sync' ), '', array( 'outofstock' => 'Mark out of stock', 'draft' => 'Set to draft', 'keep' => 'Leave as is' ) ),
				'remove_absent'        => array( 'select', __( 'If removed from feed', 'aosom-catalogue-sync' ), '', array( 'none' => 'Do nothing', 'outofstock' => 'Mark out of stock', 'draft' => 'Set to draft' ) ),
				'manage_stock'         => array( 'checkbox', __( 'Manage stock quantity', 'aosom-catalogue-sync' ), '' ),
				'import_images'        => array( 'checkbox', __( 'Import images', 'aosom-catalogue-sync' ), '' ),
				'update_existing'      => array( 'checkbox', __( 'Update existing products', 'aosom-catalogue-sync' ), '' ),
			),
			'Schedule' => array(
				'schedule_enabled' => array( 'checkbox', __( 'Enable daily sync', 'aosom-catalogue-sync' ), '' ),
				'schedule_time'    => array( 'text', __( 'Daily run time (HH:MM, site time)', 'aosom-catalogue-sync' ), '' ),
				'batch_size'       => array( 'number', __( 'Batch size', 'aosom-catalogue-sync' ), '' ),
			),
		);
	}

	public function render() {
		if ( ! current_user_can( self::CAP ) ) {
			wp_die( esc_html__( 'You do not have permission to access this page.', 'aosom-catalogue-sync' ) );
		}
		$s      = $this->settings->get();
		$fields = $this->fields();
		$action = admin_url( 'admin-post.php' );
		$last   = ACS_Logger::last_run();
		?>
		<div class="wrap">
			<h1><?php esc_html_e( 'Catalogue Sync for WooCommerce', 'aosom-catalogue-sync' ); ?></h1>
			<p class="description">
				<?php esc_html_e( 'Selling price = (regular product price + shipping) × (1 + markup%). Always run a Dry-run preview before going live.', 'aosom-catalogue-sync' ); ?>
			</p>

			<?php $this->render_last_run( $last ); ?>

			<h2><?php esc_html_e( 'Actions', 'aosom-catalogue-sync' ); ?></h2>
			<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;">
				<?php $this->action_button( 'acs_test_feed', __( 'Test feed & detect columns', 'aosom-catalogue-sync' ) ); ?>
				<?php $this->action_button( 'acs_dry_run', __( 'Dry-run preview (first 100)', 'aosom-catalogue-sync' ), 'button-secondary' ); ?>
				<?php $this->action_button( 'acs_run_now', __( 'Run full sync now', 'aosom-catalogue-sync' ), 'button-primary' ); ?>
			</div>

			<form method="post" action="<?php echo esc_url( $action ); ?>">
				<input type="hidden" name="action" value="acs_save" />
				<?php wp_nonce_field( 'acs_save', 'acs_nonce' ); ?>
				<?php foreach ( $fields as $section => $group ) : ?>
					<h2><?php echo esc_html( $section ); ?></h2>
					<table class="form-table" role="presentation"><tbody>
						<?php foreach ( $group as $key => $def ) : ?>
							<tr>
								<th scope="row"><label for="<?php echo esc_attr( $key ); ?>"><?php echo esc_html( $def[1] ); ?></label></th>
								<td><?php $this->render_field( $key, $def, $s ); ?>
									<?php if ( ! empty( $def[2] ) ) : ?>
										<p class="description"><?php echo esc_html( $def[2] ); ?></p>
									<?php endif; ?>
								</td>
							</tr>
						<?php endforeach; ?>
					</tbody></table>
				<?php endforeach; ?>
				<?php submit_button( __( 'Save settings', 'aosom-catalogue-sync' ) ); ?>
			</form>
		</div>
		<?php
	}

	private function render_field( $key, $def, $s ) {
		$type  = $def[0];
		$value = isset( $s[ $key ] ) ? $s[ $key ] : '';
		switch ( $type ) {
			case 'checkbox':
				printf(
					'<label><input type="checkbox" id="%1$s" name="%1$s" value="1" %2$s /> %3$s</label>',
					esc_attr( $key ),
					checked( ! empty( $value ), true, false ),
					esc_html__( 'Enabled', 'aosom-catalogue-sync' )
				);
				break;
			case 'select':
				echo '<select id="' . esc_attr( $key ) . '" name="' . esc_attr( $key ) . '">';
				foreach ( $def[3] as $ov => $ol ) {
					printf( '<option value="%s" %s>%s</option>', esc_attr( $ov ), selected( $value, $ov, false ), esc_html( $ol ) );
				}
				echo '</select>';
				break;
			case 'textarea':
				printf( '<textarea id="%1$s" name="%1$s" rows="4" class="large-text code">%2$s</textarea>', esc_attr( $key ), esc_textarea( $value ) );
				break;
			case 'number':
				printf( '<input type="number" step="0.01" id="%1$s" name="%1$s" value="%2$s" class="regular-text" />', esc_attr( $key ), esc_attr( $value ) );
				break;
			case 'url':
				printf( '<input type="url" id="%1$s" name="%1$s" value="%2$s" class="large-text" />', esc_attr( $key ), esc_attr( $value ) );
				break;
			default:
				printf( '<input type="text" id="%1$s" name="%1$s" value="%2$s" class="regular-text" />', esc_attr( $key ), esc_attr( $value ) );
		}
	}

	private function action_button( $action, $label, $class = 'button' ) {
		printf(
			'<form method="post" action="%s" style="margin:0;">
				<input type="hidden" name="action" value="%s" />
				%s
				<button type="submit" class="button %s">%s</button>
			</form>',
			esc_url( admin_url( 'admin-post.php' ) ),
			esc_attr( $action ),
			wp_nonce_field( $action, $action . '_nonce', true, false ),
			esc_attr( $class ),
			esc_html( $label )
		);
	}

	private function render_last_run( $last ) {
		if ( ! $last ) {
			return;
		}
		$c = $last['counters'];
		echo '<div class="notice notice-info inline"><p><strong>' . esc_html__( 'Last run:', 'aosom-catalogue-sync' ) . '</strong> ';
		echo esc_html( ( $last['dry'] ? 'Dry-run' : 'Sync' ) . ' at ' . date_i18n( 'Y-m-d H:i', $last['time'] ) . sprintf( ' — created %d, updated %d, skipped %d, errors %d.', $c['created'], $c['updated'], $c['skipped'], $c['errors'] ) );
		echo '</p></div>';

		if ( ! empty( $last['preview'] ) ) {
			echo '<details style="margin:10px 0;"><summary style="cursor:pointer;font-weight:600;">' . esc_html__( 'Price preview (from last dry-run)', 'aosom-catalogue-sync' ) . '</summary>';
			echo '<table class="widefat striped" style="margin-top:8px;"><thead><tr>';
			echo '<th>SKU</th><th>Title</th><th>Action</th><th>Sell price</th><th>Cost (prod+ship)</th><th>Detail</th></tr></thead><tbody>';
			foreach ( array_slice( $last['preview'], 0, 200 ) as $r ) {
				printf(
					'<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>',
					esc_html( $r['sku'] ),
					esc_html( isset( $r['title'] ) ? wp_trim_words( $r['title'], 8 ) : '' ),
					esc_html( $r['action'] ),
					esc_html( isset( $r['price'] ) ? number_format( (float) $r['price'], 2 ) : '' ),
					esc_html( isset( $r['cost'] ) ? number_format( (float) $r['cost'], 2 ) : '' ),
					esc_html( $r['detail'] )
				);
			}
			echo '</tbody></table></details>';
		}
	}

	/* ------------------------------------------------------------------ */
	/* Action handlers                                                     */
	/* ------------------------------------------------------------------ */

	public function handle_save() {
		$this->guard( 'acs_save', 'acs_nonce' );
		$this->settings->save( $_POST );
		$this->redirect_with_notice( __( 'Settings saved.', 'aosom-catalogue-sync' ), 'success' );
	}

	public function handle_test_feed() {
		$this->guard( 'acs_test_feed', 'acs_test_feed_nonce' );
		$s    = $this->settings->get();
		$feed = new ACS_Feed( $s );
		$dl   = $feed->download();
		if ( is_wp_error( $dl ) ) {
			$feed->cleanup();
			$this->redirect_with_notice( __( 'Feed download failed: ', 'aosom-catalogue-sync' ) . $dl->get_error_message(), 'error' );
		}
		$header = $feed->header();
		$feed->cleanup();
		if ( is_wp_error( $header ) ) {
			$this->redirect_with_notice( __( 'Could not read header: ', 'aosom-catalogue-sync' ) . $header->get_error_message(), 'error' );
		}

		// Which mapped columns exist in the header?
		$map_keys = array( 'map_sku', 'map_title', 'map_regular_price', 'map_shipping_price', 'map_discount_price', 'map_stock', 'map_category', 'map_image' );
		$missing  = array();
		foreach ( $map_keys as $mk ) {
			$col = $s[ $mk ];
			if ( '' !== $col && ! in_array( $col, $header, true ) ) {
				$missing[] = $col;
			}
		}
		$msg = sprintf( __( 'Feed OK. %d columns: ', 'aosom-catalogue-sync' ), count( $header ) ) . implode( ' | ', array_map( 'sanitize_text_field', $header ) );
		if ( $missing ) {
			$msg .= ' — ' . __( 'WARNING, mapped columns not found: ', 'aosom-catalogue-sync' ) . implode( ', ', $missing );
			$this->redirect_with_notice( $msg, 'error' );
		}
		$this->redirect_with_notice( $msg, 'success' );
	}

	public function handle_dry_run() {
		$this->guard( 'acs_dry_run', 'acs_dry_run_nonce' );
		$importer = new ACS_Importer( $this->settings->get() );
		$importer->run( true, 100 );
		$this->redirect_with_notice( __( 'Dry-run complete. See the price preview below.', 'aosom-catalogue-sync' ), 'success' );
	}

	public function handle_run_now() {
		$this->guard( 'acs_run_now', 'acs_run_now_nonce' );
		// Run asynchronously so the request returns promptly.
		wp_schedule_single_event( time() + 5, ACS_CRON_HOOK );
		spawn_cron();
		$this->redirect_with_notice( __( 'Full sync scheduled to start in the background. Refresh in a minute to see results.', 'aosom-catalogue-sync' ), 'success' );
	}

	/* ------------------------------------------------------------------ */

	private function guard( $action, $nonce_field ) {
		if ( ! current_user_can( self::CAP ) ) {
			wp_die( esc_html__( 'Insufficient permissions.', 'aosom-catalogue-sync' ) );
		}
		if ( ! isset( $_POST[ $nonce_field ] ) || ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST[ $nonce_field ] ) ), $action ) ) {
			wp_die( esc_html__( 'Security check failed.', 'aosom-catalogue-sync' ) );
		}
	}

	private function redirect_with_notice( $message, $type ) {
		set_transient( 'acs_notice_' . get_current_user_id(), array( 'm' => $message, 't' => $type ), 60 );
		wp_safe_redirect( admin_url( 'admin.php?page=' . self::SLUG ) );
		exit;
	}

	public function maybe_render_transient_notice() {
		$key = 'acs_notice_' . get_current_user_id();
		$n   = get_transient( $key );
		if ( ! $n ) {
			return;
		}
		delete_transient( $key );
		$class = 'error' === $n['t'] ? 'notice-error' : 'notice-success';
		echo '<div class="notice ' . esc_attr( $class ) . ' is-dismissible"><p>' . esc_html( $n['m'] ) . '</p></div>';
	}
}
