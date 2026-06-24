Card payments run via **Stripe Connect**: each organisation connects its own Stripe account. Payouts go to the organisation, not the hire company.

## Connect Stripe account

1. Open **Organisations** and select the organisation
2. In **Card payments (Stripe)** click **Connect with Stripe**
3. Complete Stripe onboarding in the new window
4. After returning click **Refresh status** — payments and payouts should be active

## Enable for event

In event configuration under master data enable the payment type **Card (Stripe Terminal)**.

## Requirements at point of sale

Card payment is only available when:

- the Android app with Stripe Terminal Bridge is used
- the Pi has a connection to the cloud (internet)
- the event has the payment type enabled

Without these conditions the card button in the waiter app is disabled.

## Flow at the register

1. Waiter selects **Card**
2. Pi creates a payment intent via the cloud
3. Android app collects the card via tap to pay
4. Order is recorded as paid

## Troubleshooting

- **Incomplete onboarding** — continue onboarding in Stripe and refresh status
- **Payments pending** — check Stripe account; complete details and verification
- **Card disabled on Pi** — check cloud connectivity and Android app
