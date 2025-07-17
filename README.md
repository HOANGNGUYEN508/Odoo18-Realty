# Realty BDS Customization Suite for Odoo 18

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE) [![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/HOANGNGUYEN508/Odoo18-Realty/actions)

> A comprehensive Odoo 18 modules suite for real estate listings, advanced filtering, image handling, and full company-isolation security.

---

## 📋 Table of Contents

* [About](#about)
* [Architecture](#architecture)
* [Features](#features)
* [Prerequisites](#prerequisites)
* [Installation & Setup](#installation--setup)
* [Usage](#usage)
* [Development & Workflow](#development--workflow)
* [Module Deliverables](#module-deliverables)

  * [Spring 1](#spring-1)
  * [Spring 2](#spring-2)
* [Contributing](#contributing)
* [License](#license)

---

## 📝 About

This repository contains a suite of enhancements and custom modules for **Odoo 18 Community** tailored to real estate management (Bất Động Sản). It introduces:

* Fine‑grained **company isolation** via security rules and record‑level access controls.
* A **filtering UI** with dropdowns, tag‑based domain filters, and saved preferences.
* Custom **Kanban** and **List** views for property listings.
* Rich **image widgets**: drag‑and‑drop uploads, lightbox preview, cover photo selection, hasing name.

---

## 🏛 Architecture

The project splits into multiple sub‑modules and data files:

* **Administrative Areas**: custom models for District, Commune, Regions; extending 'res.country.state' for Province/State (Huy).
* **User & Roles**: extended `res.users`, `res.partner`, `res.company`, custom signup and department wizards (Khải).
* **Product & Realty**: enhancements on `product.template` for property listings (Hoàng).
* **Security**: `res.groups`, `ir.rule`, `ir.model.access.csv` for company isolation. 'policy' for banning word (Khải & Hoàng).
* **UI**: custom profile page (Phương). Advanced Filtering UI (Hoàng).
* **UI Components**: custom field widgets and components (many2many_chip, many2many_image, photo_lightbox, validated_file_input) (Hoàng).
* **Realty Attributes**: various custom models that hold real estate's atrributes 'type', 'reason', 'status', 'land_tittle', 'feature', 'unit_price', 'home_direction', 'group_home_direction' (Hoàng & Hiếu & Khải & Huy).
* **Supporting Data**: initial data for `hr.job`, `unit_price`, 'ir.rule', 'res.groups', 'data_recycle.model' and image hashing parameters ('ir.config_parameter') (Hoàng).

---

## ✨ Features

* **Company Isolation**
  * Users from other companies can only interact with their own records but can still read base company records; they cannot CUD with those.
  * Restrict access to records by user's company via `ir.rule` and model access.
  * Custom groups and roles for base company admin and other company admistrator role (they can freely set roles themselve if they want but still follow company isolation rule).

* **Advanced Filtering UI**

  * Replace default odoo's search bar with a button that once click will open a dialog that hold dropdowns (many2one/many2many) and range inputs.
  * Tag‑based filter badges in view with removal controls.
  * Save filter preferences to `ir.filters`, set defaults, and manage via dropdown in filter diaglog.

* **Realty Listing Views**

  * Kanban cards with avatar image, key attributes, and tag chips.
  * List view enhancements for quick scanning.

* **Custom Component**

  * **many2many_image**: field widget drag‑and‑drop uploads or via select in file chooser, thumbnail grid, set cover photo, delete, download.
  * **photo_lightbox**: view image in full‑size originals, set cover photo, delete, download.
  * **validated_file_input**: file validation (image types only, ≤5 MB each, max 5 images).
  * **many2many_chip**: readonly field widget for many2many type that can be freely set how many tags appear at once (become +... if it's above the maximum amount).

* **Administrative Boundaries**

  * Models for Regions, Province/State (leveraging `res.country.state`), District, Commune.
  * FK links between geographic models and property records.

* **User & Department Wizards**

  * Add Employee to Department wizard on Department form.
  * Create Basic User wizard with assigned `hr.job` titles.

---

## ⚙️ Prerequisites

To run this suite in a containerized environment, ensure you have:

* **Docker** (Engine & Compose)
* **PostgreSQL 16** (via Docker service)

**Odoo Add‑ons Dependencies** (to be included in your `addons_path`):

```yaml
- base
- mail
- auth_signup
- web
- contacts
- VietNam_administrative
- hr
- product
- data_recycle
- calendar
```

This project’s modules (`realty_bds` and `VietNam_administrative`) should reside side‑by‑side in the same folder.

---

## 🚀 Installation & Setup

1. **Clone the repo**

   ```bash
   git clone https://github.com/HOANGNGUYEN508/Odoo18-Realty.git
   cd Odoo18-Realty
   ```

2. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Add modules to Odoo addons path** (e.g., in `odoo.conf`):

   ```ini
   addons_path = /path/to/odoo/addons,/path/to/Odoo18-Realty/realty_bds
   ```

4. **Initialize and upgrade**

   ```bash
   ./odoo-bin -c config/odoo.conf -d <your_db> --init realty_bds
   # Or to upgrade:
   ./odoo-bin -c config/odoo.conf -d <your_db> --upgrade realty_bds
   ```

5. **Restart Odoo** and log in as your admin user.

---

## ⚡️ Usage

* **Real Estate Module** available under `Realty → Properties`.
* Use the **Filters** dropdown to apply and save custom domains.
* Create or import properties; upload images via drag‑and‑drop.
* Configure `hr.job` titles for user roles and test company isolation.

---

## 🛠 Development & Workflow

* **Branching**: feature branches off `main`, PRs for review.
* **Code style**: follow Odoo 18 Python & XML conventions.
* **Testing**: manual QA in sandbox before merging.
* **CI/CD**: Actions run lint checks and Python tests on each PR.

---

## 📆 Module Deliverables

### 🎯 Spring 1

| Models & Components                                | Owner |     Status    |
| -------------------------------------------------- | ----- | :-----------: |
| `muc_dich_mua`, `dac_diem_bds`                     | Hiếu  |  ✅ Completed  |
| `chuc_danh`, `phan_quyen_chuc_danh`                | Khải  |  ✅ Completed  |
| `huong_nha`, `group_huong_nha`                     | Huy   |  ✅ Completed  |
| `khu_vuc`, `province/state`, `district`, `commune` | Huy   | ❌ In Progress |
| `hien_trang`, `tag`, `loai_hinh`, `policy`         | Hoàng |  ✅ Completed  |

### 🎯 Spring 2

| Area        | Tasks                                                                                       | Owner(s)      |    Status    |
| ----------- | ------------------------------------------------------------------------------------------- | ------------- | :----------: |
| Security    | Extend `res.users`, `res.partner`, `res.company`; `ir.rule` & `ir.model.access.csv` setup   | Khải & Hoàng  | ✅ Completed |
| Wizard      | Employee & User creation wizards                                                            | Khải          | ✅ Completed |
| Components  | `many2many_chip`, `many2many_image`, `photo_lightbox`, `validated_file_input`               | Hoàng         | ✅ Completed |
| Filter      | Filter for 'product.template'                                                               | Hoàng         | ✅ Completed |
| Data        | `hr.job`, `unit_price`, 'ir.rule', 'res.groups', 'data_recycle.model', 'ir.config_parameter'| Hoàng         | ✅ Completed |
| Refactor    | Admin area models → `res.country.state`; isolate to separate VN‑admin module                | Huy           | ✅ Completed |
| Standardize | Change model name, code from Vietnamese to English + merge code                             | Khải & Hoàng  | ✅ Completed |
| Profile UI  | Upgrade profile page with changing password and better UI                                   | Phương        | ✅ Completed |

---

## 🤝 Contributing

We welcome contributions! Please review [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on:

* Issue reporting & labeling
* Branch naming conventions
* Commit message style
* Pull request review process0

---

## 📄 License

This project is licensed under the **MIT License** – see the [LICENSE](./LICENSE) file for details.

---

*Built with ❤️ by the Realty BDS Team.*
