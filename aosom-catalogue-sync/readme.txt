=== Aosom & CSV Catalogue Sync for WooCommerce ===
Contributors: digiadagency
Tags: woocommerce, dropshipping, csv, import, aosom, feed
Requires at least: 6.0
Tested up to: 6.7
Requires PHP: 7.4
Stable tag: 0.2.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Import and daily-sync products from a CSV feed (Aosom UK or any CSV) into WooCommerce, with a safe, configurable, preview-able pricing engine.

== Description ==

This plugin imports products from a CSV product feed into WooCommerce and keeps
them in sync on a daily schedule. It was built to fix a specific, expensive
problem with dropshipping feeds: **wrong prices**.

Aosom's UK feed lists the **product price** and the **shipping price** in
separate columns (both include VAT), plus a separate **discount/promo** price.
A naive importer that reads only one price column, or the discount column, and
ignores shipping will publish products *below* what the supplier actually
charges — leading to orders that cannot be fulfilled profitably.

This plugin instead computes:

    selling price = (regular product price + shipping price) x (1 + markup%)

and **refuses to publish any product whose computed price is at or below cost**.

= Key features =

* Works with any CSV feed — every column is remappable, so it survives the
  supplier changing their column names.
* Category-flexible: filter by source category, SKU prefix or title keyword, and
  map source categories to WooCommerce categories. The same plugin can run a pet
  store, a furniture store or an exercise-equipment store from one feed.
* Safe pricing engine with markup %, flat handling fee, charm rounding and a
  minimum-margin safety floor.
* **Dry-run preview**: see every computed price in a table *before* anything goes
  live. This is the safeguard that prevents mis-priced products.
* Stock sync, image import (idempotent), draft/publish control, and a policy for
  products that disappear from the feed.
* Daily WP-Cron schedule plus a WP-CLI command (`wp acs sync [--dry-run]`).
* HPOS compatible.

== Installation ==

1. Upload the plugin zip via Plugins > Add New > Upload Plugin, or extract it to
   `wp-content/plugins/`.
2. Activate it. WooCommerce must be active.
3. Go to WooCommerce > Catalogue Sync.
4. Paste your feed URL and click "Test feed & detect columns" to confirm the
   column names, then set the column mapping.
5. Set the markup (10) and pricing options.
6. Click "Dry-run preview" and check the prices look right.
7. When happy, enable the daily schedule and/or click "Run full sync now".

== Frequently Asked Questions ==

= Does this place orders with Aosom automatically? =
No. Aosom has no UK order API, so fulfilment stays manual — the source product
URL is stored on each product to make manual ordering quick. Use DSers / sezamds
for AliExpress/Alibaba order automation.

= Will it ever sell below cost? =
No. If the computed price does not clear (product + shipping), optionally plus an
extra safety margin, the product is skipped or saved as a draft and logged.

== Changelog ==

= 0.2.0 =
* Add a "Price units" setting (pounds vs pence/cents) so prices from the Aosom
  API (minor units) and the CSV feed (pounds) are never read 100x out.

= 0.1.0 =
* Initial release: configurable CSV import, safe pricing engine, dry-run preview,
  stock + image sync, daily schedule, WP-CLI command.
