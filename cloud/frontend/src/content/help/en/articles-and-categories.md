Articles and categories form your organisation's sales catalogue. Events reference this data.

## Article categories

Categories structure the catalogue (e.g. drinks, food). Create categories first before assigning articles.

## Create articles

For each article define at least:

- **Name** and optionally a description
- **Category**
- **Price** in the organisation currency
- **Availability** — use the **Active** checkbox; inactive articles stay in the catalogue but cannot be selected for new station assignments or addition links. Already linked additions and station assignments keep working on Pi.

Add-ons and variants extend articles with configurable extras. On the article detail page, **Save** persists the article together with its linked additions and ingredients (when those sections apply). After create or update you remain on the detail so you can continue editing.

## Relation to events

Articles are not duplicated per event. In event configuration under **App layouts** you choose which articles appear on which layouts.

## Stock and event prices

Stock levels and optional event prices are maintained under **Stock items**, not in the global article master. **Catalogue price** comes from the article catalogue; an empty **Event price** field uses that catalogue price. A set event price applies only to that event (including additions in the list).

## Tips

- Consistent categories simplify layout maintenance
- Inactive articles remain in the master but do not appear in new station or layout assignments
- Catalogue price changes apply to events without an override; overrides remain until cleared
- Running events pick up updated prices on the next catalogue bundle pull
