<?php
/**
 * Pricing engine.
 *
 * This is the component that caused the refunds in the previous plugin, so it
 * is deliberately explicit and defensive. The rule, per the agreed policy:
 *
 *   selling price = (regular_product_price + shipping_price) x (1 + markup%)
 *
 * Key safeguards:
 *   - Uses the REGULAR price column, never the discount/promo column (unless
 *     explicitly overridden in settings).
 *   - Bakes delivery into the price (product + shipping) so an order can never
 *     be accepted below what Aosom actually charges.
 *   - Refuses to produce a price at or below cost; such rows are flagged so the
 *     importer can skip or draft them instead of publishing a loss-maker.
 *   - Treats a missing or zero price as an error, never as "free".
 *
 * @package AosomCatalogueSync
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

class ACS_Pricing {

	/**
	 * @var array Settings.
	 */
	private $s;

	/**
	 * @param array $settings Resolved settings array.
	 */
	public function __construct( array $settings ) {
		$this->s = $settings;
	}

	/**
	 * Compute the selling price for one feed row.
	 *
	 * @param float      $regular_product Regular product price (inc VAT, excl shipping).
	 * @param float      $shipping        Shipping price (inc VAT).
	 * @param float|null $discount        Discount/promo price (inc VAT), if any.
	 *
	 * @return array {
	 *     @type bool   $ok        True if a valid, publishable price was produced.
	 *     @type float  $price     Final selling price (0.0 if not ok).
	 *     @type float  $cost      Reference cost used for the safety floor.
	 *     @type string $reason    Human-readable reason when $ok is false.
	 * }
	 */
	public function compute( $regular_product, $shipping, $discount = null ) {
		$regular_product = $this->price_in( $regular_product );
		$shipping        = $this->price_in( $shipping );
		$discount        = ( null === $discount || '' === $discount ) ? null : $this->price_in( $discount );

		// 1) Validate inputs. A zero/negative regular price is never valid.
		if ( $regular_product <= 0 ) {
			return $this->fail( __( 'Missing or zero regular product price.', 'aosom-catalogue-sync' ) );
		}
		if ( $shipping < 0 ) {
			$shipping = 0.0;
		}

		// 2) Reference cost for the safety floor is ALWAYS the real landed figure:
		//    regular product price + shipping. We never let the sell price fall
		//    below this, whatever the pricing source.
		$cost = $regular_product + $shipping;

		// 3) Choose the base figure to mark up.
		if ( 'discount' === $this->s['price_source'] ) {
			if ( null === $discount || $discount <= 0 ) {
				// Asked to price off discount but none present: fall back to regular.
				$base_item = $regular_product;
			} else {
				$base_item = $discount;
			}
		} else {
			$base_item = $regular_product;
		}

		// 4) Add shipping into the base unless configured to charge it separately.
		$base = ( 'product_only' === $this->s['base_mode'] ) ? $base_item : ( $base_item + $shipping );

		// 5) Apply markup and flat handling fee.
		$markup   = 1 + ( (float) $this->s['markup_percent'] / 100 );
		$handling = (float) $this->s['handling_fee'];
		$price    = ( $base * $markup ) + $handling;

		// 6) Rounding (charm pricing etc.).
		$price = $this->round_price( $price );

		// 7) Safety floor: price must clear cost plus any required min margin.
		//    (When charging shipping separately, the floor is the product cost only,
		//     since delivery is recovered via the shipping method.)
		$floor_cost = ( 'product_only' === $this->s['base_mode'] ) ? $regular_product : $cost;
		$min_margin = 1 + ( (float) $this->s['min_margin_percent'] / 100 );
		$floor      = $floor_cost * $min_margin;

		if ( $price < $floor ) {
			return array(
				'ok'     => false,
				'price'  => 0.0,
				'cost'   => $cost,
				'reason' => sprintf(
					/* translators: 1: computed price, 2: required floor */
					__( 'Computed price %1$s is below the safety floor %2$s; refusing to publish a below-cost product.', 'aosom-catalogue-sync' ),
					$this->money( $price ),
					$this->money( $floor )
				),
			);
		}

		return array(
			'ok'     => true,
			'price'  => $price,
			'cost'   => $cost,
			'reason' => '',
		);
	}

	/**
	 * Apply the configured rounding strategy.
	 *
	 * @param float $price Raw price.
	 * @return float
	 */
	public function round_price( $price ) {
		switch ( $this->s['rounding'] ) {
			case 'charm_99':
				// Round UP to the next whole pound, then drop a penny => x.99.
				return max( 0.99, ceil( $price ) - 0.01 );
			case 'charm_95':
				return max( 0.95, ceil( $price ) - 0.05 );
			case 'nearest_1':
				return (float) round( $price );
			case 'nearest_050':
				return (float) ( round( $price * 2 ) / 2 );
			case 'none':
			default:
				return (float) round( $price, 2 );
		}
	}

	/**
	 * Parse a price field and convert to major units (pounds) for internal use.
	 * Aosom's API quotes prices in minor units (pence); the CSV feed is in
	 * pounds. The 'price_unit' setting selects which, so a value can never be
	 * read 100x out.
	 *
	 * @param mixed $value Raw price field.
	 * @return float Amount in major currency units (pounds).
	 */
	private function price_in( $value ) {
		$amount = $this->to_float( $value );
		if ( isset( $this->s['price_unit'] ) && 'minor' === $this->s['price_unit'] ) {
			$amount = $amount / 100;
		}
		return $amount;
	}

	/**
	 * Parse a feed price string into a float. Handles currency symbols,
	 * thousands separators and stray whitespace.
	 *
	 * @param mixed $value Raw.
	 * @return float
	 */
	public function to_float( $value ) {
		if ( is_numeric( $value ) ) {
			return (float) $value;
		}
		$value = (string) $value;
		// Strip everything except digits, dot, comma and minus.
		$value = preg_replace( '/[^0-9.,\-]/', '', $value );
		if ( '' === $value ) {
			return 0.0;
		}
		// If both separators present, assume comma = thousands, dot = decimal.
		if ( false !== strpos( $value, '.' ) && false !== strpos( $value, ',' ) ) {
			$value = str_replace( ',', '', $value );
		} else {
			// Single comma -> treat as decimal separator (EU style).
			$value = str_replace( ',', '.', $value );
		}
		return is_numeric( $value ) ? (float) $value : 0.0;
	}

	/**
	 * Build a failure result.
	 *
	 * @param string $reason Reason text.
	 * @return array
	 */
	private function fail( $reason ) {
		return array(
			'ok'     => false,
			'price'  => 0.0,
			'cost'   => 0.0,
			'reason' => $reason,
		);
	}

	/**
	 * Format money for log messages (no HTML).
	 *
	 * @param float $amount Amount.
	 * @return string
	 */
	private function money( $amount ) {
		return number_format( (float) $amount, 2 );
	}
}
