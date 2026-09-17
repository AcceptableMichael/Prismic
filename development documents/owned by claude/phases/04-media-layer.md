# Phase 4 — Media layer

Goal: images and WebM video actually decode, display, and play smoothly, with
a concrete tested definition of "supported" rather than "every extension we
found." Corresponds to overview sections 8 and 9.

## Supported-format definition

- [ ] Concrete list of supported image formats (from Qt's conventional
      supported set — pick and document which ones, don't just claim "all of
      them")
- [ ] WebM video support defined by the actual codecs the chosen playback
      stack (Qt Multimedia) provides, validated against fixtures, not assumed
- [ ] Audio accompanying supported video plays when present
- [ ] Extension is only a candidate filter (used by the Phase 2 scanner) —
      actual decoding is what determines validity here
- [ ] Document animated-image behavior as "whatever the chosen Qt image
      stack actually does," backed by a fixture — no unvalidated promises
      beyond that

## Test fixtures (`tests/fixtures/`)

- [ ] Supported image
- [ ] Large image (large enough to exercise downsampling/caching behavior)
- [ ] Corrupt image
- [ ] Supported WebM
- [ ] Audio-bearing WebM
- [ ] Unsupported media (extension not supported, and/or a supported
      extension with invalid content)

## Loading (`media/loader.py`, `media/image.py`, `media/video.py`)

- [ ] Image decode path, off the GUI thread
- [ ] Video load/playback path via the chosen Qt media backend
- [ ] Corrupt/invalid media surfaces as a handled error state, not a crash
- [ ] Every load/decode/preload request carries a generation/request id

## Caching (`media/cache.py`)

- [ ] Bounded cache — large images are not retained indefinitely at full
      decoded resolution
- [ ] Appropriate downsampling for display size
- [ ] Eviction of obsolete decoded data
- [ ] Preloading of likely-next items without unbounded memory growth

## Staleness under rapid navigation

- [ ] Stale decode/load results are discarded before they can replace the
      currently displayed media (generation-id check, same mechanism family
      as Phase 2's scan staleness)
- [ ] Rapid back-to-back navigation does not cause flicker to a
      previously-requested (now stale) item

## Tests (`tests/unit`, `tests/integration`)

- [ ] Supported image loads and decodes correctly
- [ ] Large image is downsampled/cached within bounds, not held at full res
      indefinitely
- [ ] Corrupt image produces a handled error, not a crash
- [ ] Supported WebM loads and plays
- [ ] Audio-bearing video plays audio
- [ ] Unsupported media is rejected cleanly
- [ ] Rapid navigation: stale loads are suppressed and never clobber the
      current item
