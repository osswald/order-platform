## 1. Audio asset & attribution

- [x] 1.1 Download Commons Dial up modem noises.ogg and trim to the first 15 seconds; commit as `android/app/src/main/res/raw/modem56k.ogg` (or preferred Android-compatible format)
- [x] 1.2 Add a short attribution note (source URL, William Termini, public domain, first 15 seconds)

## 2. Android bridge (tests first)

- [x] 2.1 Write Kotlin unit tests for volume save → set ~75% → restore, and for soft-fail when playback cannot start
- [x] 2.2 Implement MediaPlayer + AudioManager handshake helper and expose it on `AndroidApp` (start + completion/failure signal to WebView)
- [x] 2.3 Wire cleanup on Activity destroy so volume is restored and MediaPlayer is released if the egg is interrupted
- [x] 2.4 Run Android unit tests

## 3. Pi frontend easter egg (tests first)

- [x] 3.1 Write Vitest coverage: name match (`edi` / `Edi`), non-match skip, non-Android skip, soft-fail still navigates to hub
- [x] 3.2 Add TypeScript typings for the new `AndroidApp` handshake API in `env.d.ts`
- [x] 3.3 Implement overlay UI (spinner + `Connecting...`) and login hook that awaits native handshake before hub navigation
- [x] 3.4 Run Pi frontend tests for touched areas

## 4. Verification

- [x] 4.1 Run Android + Pi frontend tests and `./scripts/lint.sh` for touched areas
- [x] 4.2 Manual smoke on device/emulator: Edi login hears modem + volume restores; other waiter unchanged; force audio failure path if feasible
