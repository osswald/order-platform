# Stripe Connect and Terminal integration (removed)

> **Deprecated:** Vendiqo no longer integrates Stripe Connect or Stripe Terminal Tap to Pay.
> See [`sumup-cloud-api.md`](sumup-cloud-api.md) for the current card payment stack (SumUp Cloud API).

The content below is kept only as historical reference from before the SumUp migration.

---

Organisations connect their own Stripe account in the cloud admin UI. In-person
contactless payments run on Android waiter devices via **Tap to Pay** (Stripe
Terminal SDK). Raspberry Pi and Android never receive the platform Stripe secret;
they use Pi-local APIs that proxy to cloud edge endpoints with existing appliance
credentials.

*(Remaining sections unchanged from the original document — no longer applicable to production.)*
