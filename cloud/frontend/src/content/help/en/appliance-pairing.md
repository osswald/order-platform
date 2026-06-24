Raspberry Pi servers connect to the cloud via pairing. This synchronises events, articles, and orders.

## Prerequisites

1. Create an appliance of type **Server** under **Appliances**
2. Generate a **pairing code** in the appliance detail
3. Start the Pi on the network and open the local setup page (e.g. `http://192.168.192.10`)

## Perform pairing

1. Enter the pairing code on the Pi setup page
2. The Pi calls the cloud API and receives credentials
3. After successful pairing the Pi loads event bundles and synchronises orders

The **edge secret** is shown only once during pairing and stored on the Pi.

## Multiple SD cards

One server appliance can have several paired SD cards (primary and backup). Each card gets its own credentials and can be revoked individually.

**Important:** Only one SD card of the same server should be powered on at a time.

## Use a backup card

If the active SD card fails, boot an already paired backup card. The Pi continues syncing as the same server appliance.

## Revoke pairing

On the Pi, unpairing is only possible with the configured `unpair_secret`. In the cloud you can revoke individual SD cards in the appliance detail.
