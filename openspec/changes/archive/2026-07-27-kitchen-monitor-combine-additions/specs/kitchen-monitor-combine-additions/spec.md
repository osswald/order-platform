## ADDED Requirements

### Requirement: Addition links expose kitchen combine flag

The system SHALL allow tenant admins to set a boolean **Kombinieren auf Küchendisplay** (`combine_on_kitchen_display`) on each base-article → addition link, in the same additions list as **Vorauswahl Pi**. The flag SHALL default to false for existing links and for newly added links. The same addition article MAY have different flag values on different base articles.

#### Scenario: Persist combine flag with addition links

- **WHEN** an admin saves addition links for a base article including `combine_on_kitchen_display: true` for one link and `false` for another
- **THEN** a subsequent read of that article’s additions SHALL return those flag values unchanged

#### Scenario: Default false for new and existing links

- **WHEN** an addition link is created without specifying `combine_on_kitchen_display`
- **THEN** the stored value SHALL be false
- **WHEN** existing links are migrated to include the column
- **THEN** each existing link SHALL have `combine_on_kitchen_display` false

#### Scenario: Admin column next to Vorauswahl Pi

- **WHEN** an admin opens the additions list for a non-addition article
- **THEN** the list SHALL show a **Kombinieren auf Küchendisplay** control alongside **Vorauswahl Pi** for each linked Zusatz

### Requirement: Edge bundle includes combine flag on additions

When building an event edge bundle, each addition entry under a base article SHALL include `combine_on_kitchen_display` reflecting the link flag. Consumers SHALL treat a missing flag as false.

#### Scenario: Bundle addition entry carries flag

- **WHEN** a base article has a linked addition with `combine_on_kitchen_display` true
- **THEN** that addition object in the event articles map SHALL include `combine_on_kitchen_display: true`

#### Scenario: Missing flag treated as false

- **WHEN** a kitchen client reads an addition entry without `combine_on_kitchen_display`
- **THEN** the client SHALL behave as if the flag were false

### Requirement: Products view combines flagged additions under the parent

On the kitchen monitor Produkte view, open remaining quantity SHALL be aggregated by parent article, the signature of additions whose link flag is true for that parent, and the line note. Flagged additions SHALL appear on a second display line under the parent (**label**-preferred). Non-empty notes SHALL appear on a third line. Additions with flag false SHALL NOT appear on the parent card and SHALL remain aggregated as standalone product cards by addition article id.

#### Scenario: Flagged addition folds into parent card

- **WHEN** open lines include Raclette with flagged addition DOPPELT KÄSE
- **THEN** the products summary SHALL show one parent card whose second line includes the DOPPELT KÄSE addition
- **AND** DOPPELT KÄSE SHALL NOT appear as a standalone addition card for that qty

#### Scenario: Unflagged addition stays standalone

- **WHEN** open lines include a parent with an unflagged addition
- **THEN** the products summary SHALL show the parent without that addition on line 2
- **AND** SHALL show a standalone card for that addition’s remaining quantity

#### Scenario: Mixed flagged and unflagged on one line

- **WHEN** a line has both a flagged and an unflagged addition
- **THEN** the parent card SHALL list only the flagged addition(s) on line 2
- **AND** the unflagged addition SHALL contribute to its standalone card

#### Scenario: Note splits product buckets

- **WHEN** two open lines share the same parent and flagged additions but have different notes
- **THEN** the products summary SHALL show two parent cards
- **AND** each card’s third line SHALL show its respective note

#### Scenario: Plain parent without flagged additions

- **WHEN** open lines include a parent with no flagged additions and an empty note
- **THEN** the products summary SHALL aggregate that parent by article id only (single card for matching lines)

### Requirement: Kitchen monitor prefers article labels

Kitchen monitor Bestellungen and Produkte views SHALL display the article **label** when present (non-empty), otherwise **name**, for parent articles and for addition text.

#### Scenario: Label used when present

- **WHEN** an article has label `Doppelt Käse` and name `DOPPELT KÄSE EXTRA`
- **THEN** kitchen monitor product and addition text for that article SHALL show `Doppelt Käse`

#### Scenario: Name fallback when label empty

- **WHEN** an article has an empty label and name `Raclette`
- **THEN** kitchen monitor text for that article SHALL show `Raclette`

### Requirement: Produkte view has no Zusätze checkbox

The kitchen monitor Produkte view SHALL NOT offer a Zusätze visibility checkbox. Standalone (unflagged) addition cards SHALL always be included in the products list when they have open remaining quantity.

#### Scenario: Zusätze toggle absent

- **WHEN** the operator is on the kitchen Produkte view
- **THEN** the header SHALL NOT show a Zusätze checkbox
- **AND** unflagged additions with remaining qty SHALL still appear as product cards
