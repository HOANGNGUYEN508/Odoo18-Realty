# Realty BDS Customization Suite for Odoo 18

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE) [![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/HOANGNGUYEN508/Odoo18-Realty/actions)

> A comprehensive Odoo 18 modules suite for real estate listings, advanced filtering, image handling, and full company-isolation security.

---

## 📋 Table of Contents

* [Architecture](#architecture)
* [Features](#features)
* [Prerequisites](#prerequisites)
* [Installation & Setup](#installation--setup)
* [Usage](#usage)
* [Module Deliverables](#module-deliverables)

  * [Spring 1](#spring-1)
  * [Spring 2](#spring-2)
  * [Spring 3](#spring-3)
* [License](#license)

---

## 🏛 Architecture

The project splits into multiple sub‑modules and data files:

* **Administrative Areas**: custom models for District, Commune, Regions; extending 'res.country.state' for Province/State.
* **User & Roles**: extended `res.users`, `res.partner`, `res.company`, custom signup and department wizards.
* **Product & Realty**: enhancements on `product.template` for property listings.
* **Security**: `res.groups`, `ir.rule`, `ir.model.access.csv` for company isolation. 'policy' for banning word.
* **UI**: custom profile page. Advanced Filtering UI. Advanced Comment Section UI.
* **UI Components**: custom field widgets and components (many2many_chip, many2many_image, photo_lightbox, validated_file_input, boolean_subscriber).
* **Realty Attributes**: various custom models that hold real estate's atrributes 'type', 'reason', 'status', 'land_tittle', 'feature', 'unit_price', 'home_direction', 'group_home_direction'.
* **Supporting Data**: initial data for `hr.job`, `unit_price`, 'ir.rule', 'res.groups', 'data_recycle.model' and image hashing parameters ('ir.config_parameter').
* **Notify post and Comment Section**: similar to how Facebook and its comment section function.

---

## ✨ Features

* **Company Isolation**:

  * Users from other companies can only interact with their own records but can still read base company records; they cannot CUD with those.
  * Restrict access to records by user's company via `ir.rule` and model access.
  * Custom groups and roles for base company admin and other company admistrator role (they can freely set roles themselve if they want but still follow company isolation rule).

* **Advanced Filtering UI**:

  * Replace default odoo's search bar with a button that once click will open a dialog that hold dropdowns (many2one/many2many) and range inputs.
  * Tag‑based filter badges in view with removal controls.
  * Save filter preferences to `ir.filters`, set defaults, and manage via dropdown in filter diaglog.

* **Realty Listing Views**:

  * Kanban cards with avatar image, key attributes, and tag chips.
  * List view enhancements for quick scanning.

* **Custom Component**:

  * **many2many_image**: field widget drag‑and‑drop uploads or via select in file chooser, thumbnail grid, set cover photo, delete, download.
  * **photo_lightbox**: view image in full‑size originals, set cover photo, delete, download.
  * **validated_file_input**: file validation (image types only, ≤5 MB each, max 5 images).
  * **many2many_chip**: readonly field widget for many2many type that can be freely set how many tags appear at once (become +... if it's above the maximum amount).
  * **boolean_subscriber**: field widget for subscribe system when it come to `notify`,`product.template` and `realty_comment` related actions (approve, reject, remove).

* **Administrative Boundaries**:

  * Models for Regions, Province/State (leveraging `res.country.state`), District, Commune.
  * FK links between geographic models and property records.

* **User & Department Wizards**:

  * Add Employee to Department wizard on Department form.
  * Create Basic User wizard with assigned `hr.job` titles.

* **General Wizard for actions related to `notify`,`product.template`**:

  * Remove `notify` post or a product (`product.template`).
  * Approve `notify` post or a product (`product.template`) creation.
  * Reject `notify` post or a product (`product.template`) creation.

* **Wizard** for remove action done by moderator in `realty_comment`.

* **Canned Responses**: `remove_reason` and `reject_reason`.

* **Auto Moderator Assignment**: Each time a `notify` post or a product (`product.template`) create, a moderator will automatically get assign with its evalation.

* **Extend Binary Controller of Odoo**: For handling multi-company image show.

* **Hashing Controller**: a custom controller that hash image name when it got uploaded via `validated_file_input` component.

* **Group Tracker**: a permisson tracker model - `permission_tracker` - for dynamic permission mapping (model -> groups) that will be used for `notify`, `product.template` and `realty_comment`.

* **Notify post and Comment Section**:

  * Threaded, Facebook-style comments with unlimited nesting, inline replies, likes, edit, and delete.
  * Instant UI feedback via optimistic updates (client creates negative tmpId records), then reconciles with server when the real comment is saved.
  * Real-time updates via a bus channel so new comments, edits, likes and deletes appear for everyone immediately.

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

2. **Add modules to Odoo addons path** (e.g., in `odoo.conf`):

   ```ini
   addons_path = /path/to/odoo/addons,/path/to/Odoo18-Realty/realty_bds
   ```

3. **Comment** the 77th line in __manifest__.py

4. **Initialize**

   ```bash
   ./odoo-bin -c config/odoo.conf -d <your_db> --init realty_bds
   ```

5. **Log in** as your admin user, Go to "Settings" -> "Technical" -> "Security" -> "Record Rules" -> Archive these rules: "Product multi-company", "Job multi company rule"

6. **Uncomment** the 77th line in __manifest__.py

7. **Restart Odoo and upgrade**

   ```bash
   ./odoo-bin -c config/odoo.conf -d <your_db> --upgrade realty_bds
   ```

8. **Restart Odoo** and log in as your admin user.

---

## ⚡️ Usage

* **Realty_bds** available under `Real Estate` menu option.
* **VietNam_administrative** avalable under `Vietnam Administration` menu option.
* Use the **Filter** button in **Warehouse** submenu option to apply and save custom domains.
* Configure:
  * Who or which company can see your real estate via Additional Information in product's form view.
  * Which group is currently in management of model in `permission_tracker`.
  * How many time user can edit their submission attemp (`product.template` or `notify`) after rejection by changing "realty_bds.editcounter" in `ir.config_parameter`.
  * Hashing salt of image uploaded via `validated_file_input` component by changing "realty_bds.specialSalt" in `ir.config_parameter`.
  * `hr.job` for user roles.
  * Canned responses when approve, remove or reject.
  * Guideline during evaluation process.
* Upload images with drag‑and‑drop, set cover photo, download, delete via widget in product's form view.
* Admin from base company control other company real estate's property models, can create individual admin for each company but they can only interact with their own records.
* Can add employee from department's form view without visit each employee form view.
* Set up meeting date with contact of a estate.
* Make report of said meeting.
* Subscribe to a user to get notif of their action in `notify`.
* Evaluation system of `notify` or estate.
* Socialize in `notify` via comment section. 
* Moderate estate or `notify`.

---

## 📆 Module Deliverables

### 🎯 Spring 1

| Models & Components                                | Owner |     Status     |
| -------------------------------------------------- | ----- | -------------- |
| `muc_dich_mua`, `dac_diem_bds`                     | Hiếu  |  ✅ Completed  |
| `chuc_danh`, `phan_quyen_chuc_danh`                | Khải  |  ✅ Completed  |
| `huong_nha`, `group_huong_nha`                     | Huy   |  ✅ Completed  |
| `khu_vuc`, `province/state`, `district`, `commune` | Huy   | ❌ In Progress |
| `hien_trang`, `tag`, `loai_hinh`, `policy`         | Hoàng |  ✅ Completed  |

### 🎯 Spring 2

| Area        | Tasks                                                                                       | Owner(s)      |    Status    |
| ----------- | ------------------------------------------------------------------------------------------- | ------------- | ------------ |
| Security    | Extend `res.users`, `res.partner`, `res.company`; `ir.rule` & `ir.model.access.csv` setup   | Khải & Hoàng  | ✅ Completed |
| Wizard      | Employee & User creation wizards                                                            | Khải          | ✅ Completed |
| Components  | `many2many_chip`, `many2many_image`, `photo_lightbox`, `validated_file_input`               | Hoàng         | ✅ Completed |
| Filter      | Filter for 'product.template'                                                               | Hoàng         | ✅ Completed |
| Data        | `hr.job`, `unit_price`, 'ir.rule', 'res.groups', 'data_recycle.model', 'ir.config_parameter'| Hoàng         | ✅ Completed |
| Refactor    | Admin area models → `res.country.state`; isolate to separate VN‑admin module                | Huy           | ✅ Completed |
| Standardize | Change model name, code from Vietnamese to English + merge code                             | Khải & Hoàng  | ✅ Completed |
| Profile UI  | Upgrade profile page with changing password and better UI                                   | Phương        | ✅ Completed |
| Hash        | Create a custom controller for hashing image name for `validated_file_input` component      | Hoàng         | ✅ Completed |

### 🎯 Spring 3

| Area             | Tasks                                                                                                   | Owner(s)      |    Status    |
| ---------------- | ------------------------------------------------------------------------------------------------------- | ------------- | ------------ |
| Report           | Create `product_report`, `client_feedback`, `owner_feedback`                                            | Hoàng         | ✅ Completed |
| Canned responses | Create `remove_reason`, `reject_reason`                                                                 | Hoàng         | ✅ Completed |
| Notify           | Create `notify` inherit by `guideline`, `congratulation`, `notification`, `urgent_buying`               | Hoàng         | ✅ Completed |
| Comment          | Create `realty_comment` and its custom "component made" UI `realty_comment`                             | Hoàng         | ✅ Completed |
| General Wizard   | Create `notify_wizard` for approve, reject, remove action when it come to `notify`, `product.template`  | Hoàng         | ✅ Completed |
| Removal Wizard   | Creat `comment_wizard` for remove action done by moderator in `realty_comment`                          | Hoàng         | ✅ Completed |
| Guideline        | Create `moderator_guideline` for those whose role is moderator                                          | Hoàng         | ✅ Completed |
| Assign mod       | Create `moderator_assignment_sequence` and its usage for auto moderator assignment                      | Hoàng         | ✅ Completed |
| Group tracker    | Create `permission_tracker` for dynamic permission mapping (model -> groups)                            | Hoàng         | ✅ Completed |
| Subscribe system | Create a system for inbox notification when it come to `notify` and `realty_comment`                    | Hoàng         | ✅ Completed |
| Binary           | Extend Binary Controller of Odoo For handling multi-company image show                                  | Hoàng         | ✅ Completed |

---


## 📄 License

This project is licensed under the **MIT License** – see the [LICENSE](./LICENSE) file for details.

---

*Built with ❤️ by the Realty BDS Team.*
