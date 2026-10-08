# Lossless website flyer delivery

`data/events.json` and the visual-review/baseline ledgers continue to identify
the original image and its original SHA256. `data/media_delivery.json` maps an
original to a website-only WebP. This mapping is encoding evidence, not a new
visual approval. Existing unverified website baselines remain unverified.

## Publication procedure

1. Retain the approved original in private storage outside the checkout and in
   a Git commit. Record its commit, path, Git blob and SHA256. Never store private
   approval messages, social captions or account identifiers in this manifest.
2. Encode at the original dimensions with Pillow 12.3.0 WebP `lossless=True`,
   `exact=True`. Preserve ICC, EXIF and XMP. Do not resize, recolor or redesign.
3. Compare decoded RGBA bytes, dimensions and color/orientation metadata. Check
   representative originals and derivatives in desktop/mobile browsers. Keep
   the original delivery file if encoding is larger or changes the rendering.
4. Add the smaller derivative and its mapping. Remove that original from the
   current public tree only after the private copy and Git bytes are verified.
   Keep files without an adopted derivative. Do not delete archive events.
   Add a temporary Vercel redirect from the old image URL to the derivative so
   existing website links remain usable without deploying a second image copy.
5. Run `python automation/media_delivery.py`, all renderers, Python/Node tests,
   rendered publication audit and browser checks. CI needs full Git history and
   Pillow. A missing history object, changed hash or nonidentical pixel fails.
6. Publish through a reviewed PR and verify production image responses, event
   cards, detail pages, OG/JSON-LD images and both viewport sizes.

`publication_guard.image_file()` resolves original bytes from the current file,
or from the recorded immutable Git source into a process-private temporary
directory outside the public checkout. Renderers alone select the derivative.
Social approval and remote-post verification continue using original bytes and
hashes. Existing provider-hosted social images and reservations are not edited.
Do not upload the website WebP under an original-image approval.

## Recovery

Revert the image-delivery publication commit/merge, regenerate the website and
deploy normally; this restores originals and references without rewriting Git
history. For one image, restore its recorded source path from `source_commit`,
remove only its delivery mapping and generated WebP, and regenerate all views.
Remove its old-URL redirect when restoring the original delivery file.
Verify source SHA256 against the unchanged visual/baseline ledger. Private
original storage is a second recovery copy, not part of the deployment.
