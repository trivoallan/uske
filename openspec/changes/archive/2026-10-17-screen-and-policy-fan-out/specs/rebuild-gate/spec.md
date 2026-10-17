## ADDED Requirements

### Requirement: Une réparation se renouvelle sur le tag qu'elle a réparé

Quand le plan du placeur marque une opération `remediated: true` (le tag de destination qu'elle
remplace porte une réparation), le screening SHALL la rendre au placeur avec un ordre de
remédiation sous l'epoch du screening, même si la source est en `direct-placement`. Sans transit
nommé, cette opération MUST être retirée du plan rendu au placeur, et sa source consignée
`inconclusive`, raison `uske/no-transit` : la placer sans ordre déferait la réparation. Une source
refusée, close ou dont les essais sont épuisés reste retirée, comme sans la marque. Une opération
sans la clé `remediated` MUST être tenue pour non marquée. Le screening ne déduit jamais lui-même,
de la destination, qu'un tag a été réparé.

#### Scenario: Un correctif amont sur un tag réparé

- **GIVEN** une source en `direct-placement`, et un plan dont l'opération sur cette source porte
  `remediated: true`
- **WHEN** le plan est filtré avec un transit nommé
- **THEN** l'opération figure dans le plan rendu au placeur avec `remediate: {epoch: <epoch du
  screening>}`

#### Scenario: Un tag réparé, sans transit

- **GIVEN** une source en `direct-placement`, et un plan dont l'opération sur cette source porte
  `remediated: true`
- **WHEN** le plan est filtré sans transit
- **THEN** l'opération est retirée du plan rendu au placeur
- **AND** le journal gagne une ligne `inconclusive` de raison `uske/no-transit` sur la source

#### Scenario: Un tag jamais réparé

- **GIVEN** une source en `direct-placement`, et un plan dont l'opération ne porte pas
  `remediated`
- **WHEN** le plan est filtré avec un transit nommé
- **THEN** l'opération figure dans le plan rendu au placeur, sans ordre de remédiation

#### Scenario: Un tag réparé dont la nouvelle source est refusée

- **GIVEN** une source en `quarantine`, et un plan dont l'opération sur cette source porte
  `remediated: true`
- **WHEN** le plan est filtré avec un transit nommé
- **THEN** l'opération est retirée du plan rendu au placeur
