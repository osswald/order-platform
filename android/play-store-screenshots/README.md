# Play Store tablet screenshots (Vendiqo Waiter)

Real UI captures from the Play Review demo (`https://play-review.demo.vendiqo.ch`), landscape **16:9**.

## Files to upload in Google Play Console

| Play Console slot | Files |
|-------------------|--------|
| **7" tablets** | `7in-01-hub.png` … `7in-08-pay-table.png` (1280×720) |
| **10" tablets** | `10in-01-hub.png` … `10in-08-pay-table.png` (1920×1080) |

Upload order (marketing set):

1. Hub (Kellner home)
2. Events list
3. Login
4. Table keypad
5. Order (empty cart + product grid)
6. Order (filled cart) — strongest tablet landscape shot
7. Open tables
8. Pay / settle (split-pay)

## Regenerate

```bash
cd android/play-store-screenshots
npm ci   # or: npm install
npx playwright install chromium
npm test
npm run capture
npm run verify
```

Optional: `PLAY_REVIEW_URL=… TABLE_NUMBER=12 HEADED=1 npm run capture`

The capture script overrides `emulated_printer` so the hosted demo receipts rail is hidden and the tablet cart|grid layout is shown (as on the Android app).
