import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from "@web/core/utils/patch";
import { onWillStart, useState } from "@odoo/owl";
import { user } from "@web/core/user";
import { FilterDialog } from "./filter_dialog";
import { parseDomainToValues, buildDomainFromValues } from "./utils_filter";

const _origSetup = ControlPanel.prototype.setup;

patch(ControlPanel.prototype, {
	name: "realty_bds.ControlPanel",

	setup() {
		_origSetup.call(this);

		if (this.env.searchModel?.resModel === "product.template") {
			// Initialize filters & options
			this.currentFilters = {
				province_id: "",
				district_id: "",
				commune_id: "",
				region_id: "",
				status_id: "",
				type_id: "",
				land_title_id: "",
				feature_ids: [],
				min_price: "",
				max_price: "",
				unit_price_min_id: "",
				unit_price_max_id: "",
				preference_id: "",
				name: "",
				is_default: false,
			};

			this.currentOptions = {
				regions: [],
				provinces: [],
				districts: [],
				communes: [],
				statuss: [],
				types: [],
				land_titles: [],
				unit_price: [],
				features: [],
			};

			this.defaultFilters = { ...this.currentFilters };
			this.defaultOptions = { ...this.currentOptions };

			// Labels for chips
			this.label_map = {
				min_price: "Min Price",
				max_price: "Max Price",
				province_id: "Province",
				district_id: "District",
				commune_id: "Commune",
				region_id: "Region",
				status_id: "Status",
				type_id: "Type",
				land_title_id: "Land Title",
				feature_ids: "Feature",
			};

			// Expand/collapse
			this.maxVisibleChips = 6;
			this.favoriteFilter = useState({ isFavorite: false });
			this.chipState = useState({ isExpanded: false });

			// Load default filter
			onWillStart(async () => {
				const [def] = await this.orm.searchRead(
					"ir.filters",
					[
						["model_id", "=", "product.template"],
						["user_id", "=", user.userId],
						["is_default", "=", true],
					],
					["id", "domain", "context", "name", "is_default"]
				);
				if (def) {
					const values = parseDomainToValues(def.domain, def.context);
					this.currentFilters = {
						...values,
						preference_id: def.id.toString(),
						name: def.name || "",
						is_default: def.is_default === "True" || def.is_default === true,
					};
				}
			});
		}
	},

	openFilterDialog() {
		this.dialogService.add(FilterDialog, {
			applyFilter: this.applyFilterValues.bind(this),
			initialState: { ...this.currentFilters, options: this.currentOptions },
			close: () => this.dialogService.remove(),
		});
	},

	async favoriteToggle() {
		this.favoriteFilter.isFavorite = !this.favoriteFilter.isFavorite;
		await this.applyFilterValues(this.currentFilters, this.currentOptions);
	},

	async applyFilterValues(states = {}, options = {}) {
		let domain = [];
		if (Object.keys(states).length === 0) {
			this.currentFilters = { ...this.defaultFilters };
			this.currentOptions = { ...this.defaultOptions };
		} else {
			this.currentFilters = { ...states };
			this.currentOptions = { ...options };
			domain = buildDomainFromValues(states, options);
		}

		// remove top-level is_favorite tuples
		if (Array.isArray(domain) && domain.length) {
			domain = domain.filter(
				(cond) => !(Array.isArray(cond) && cond[0] === "is_favorite")
			);
		}

		// add favorite overlay if enabled
		if (this.favoriteFilter.isFavorite) {
			domain = domain.length ? [...domain, ["is_favorite", "=", true]] : [["is_favorite", "=", true]];
		}

		await this.env.searchModel.clearQuery();
		await this.env.searchModel.clearSections(
			this.env.searchModel.filters.map((f) => f.id)
		);
		await this.env.searchModel.reload({
			domain,
			context: this.env.searchModel.context,
		});
		this.env.searchModel.search();
	},

	removePreferenceChip() {
		this.applyFilterValues();
	},

	removeChip(key) {
		this.currentFilters[key] = this.defaultFilters[key] || "";
		this.applyFilterValues(this.currentFilters, this.currentOptions);
	},

	removeFeature(fid) {
		this.currentFilters.feature_ids = this.currentFilters.feature_ids.filter(
			(id) => id.toString() !== fid.toString()
		);
		this.applyFilterValues(this.currentFilters, this.currentOptions);
	},

	toggleExpand() {
		this.chipState.isExpanded = !this.chipState.isExpanded;
	},

	get allChips() {
		const { preference_id, name, is_default } = this.currentFilters;
		// Preference chip overrides all normals
		if (preference_id) {
			return [
				{
					key: "preference",
					label: name,
					removable: true,
					remove: () => this.removePreferenceChip(),
					isDefault: !!is_default,
				},
			];
		}

		// Order of normal chips
		const order = [
			"min_price",
			"max_price",
			"province_id",
			"district_id",
			"commune_id",
			"region_id",
			"status_id",
			"type_id",
			"land_title_id",
		];
		const chips = [];
		order.forEach((k) => {
			const v = this.currentFilters[k];
			if (!v) return;
			const baseLabel = this.label_map[k] || k;
			let suffix = "";
			if (k === "min_price" || k === "max_price") {
				const unitField = k.startsWith("min")
					? "unit_price_min_id"
					: "unit_price_max_id";
				suffix =
					this.currentOptions.unit_prices.find(
						(u) => u.id.toString() === this.currentFilters[unitField]
					)?.name || "";
			} else if (k.endsWith("_id")) {
				const listName = k.replace(/_id$/, "s");
				suffix =
					this.currentOptions[listName]?.find(
						(r) => r.id.toString() === v.toString()
					)?.name || "";
			}
			if (k === "min_price" || k === "max_price") {
				chips.push({
					key: k,
					label: `${baseLabel}: ${v} ${suffix ? ` ${suffix}` : ""}`,
					removable: true,
					remove: () => this.removeChip(k),
				});
			} else {
				chips.push({
					key: k,
					label: `${baseLabel}: ${suffix}`,
					removable: true,
					remove: () => this.removeChip(k),
				});
			}
		});
		// Feature chips
		this.currentFilters.feature_ids.forEach((fid) => {
			const feat = this.currentOptions.feature_ids.find(
				(d) => d.id.toString() === fid.toString()
			);
			if (feat) {
				chips.push({
					key: `feat_${fid}`,
					label: `Feature: ${feat.name}`,
					removable: true,
					remove: () => this.removeFeature(fid),
				});
			}
		});
		return chips;
	},
});
