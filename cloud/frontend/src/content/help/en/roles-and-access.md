Vendiqo distinguishes four roles. What you see in the navigation depends on your role.

## Platform admin (superuser)

Vendiqo operator with access to all hire companies.

- Create and manage hire companies (**Hire companies**)
- Choose **Active hire company** in the sidebar — API requests send the `X-Hire-Company-Id` header
- Full access within the selected hire company

## Hire company admin

Staff of a hire company with administration rights at tenant level.

- Edit own hire company master data (**Tenant settings**)
- Create and manage organisations
- Manage appliances and users across the hire company
- Plan lendings, maintain events and catalogue
- Stripe onboarding for organisations

## Organisation admin

Administrator of one or more customer organisations.

- Edit assigned organisations (no create/delete)
- Manage users only within own organisation(s)
- Events, articles, waiters, etc. in assigned organisations

## Member

User of a customer organisation.

- Assigned organisations and their events, articles, waiters
- View appliance lendings (read-only)
- No access to organisation master data or user management

## Navigation

| Area | Platform admin | Hire company admin | Organisation admin | Member |
|------|----------------|--------------------|--------------------|--------|
| Dashboard, events, catalogue | yes | yes | yes | yes (own orgs) |
| Hire companies (list) | yes | no | no | no |
| Tenant settings | yes | yes | no | no |
| Organisations | yes | yes | yes (edit) | no |
| Appliances, users | yes | yes | users (own orgs) | no |
| Settings (password) | yes | yes | yes | yes |

If access is missing the application redirects to an information page.
