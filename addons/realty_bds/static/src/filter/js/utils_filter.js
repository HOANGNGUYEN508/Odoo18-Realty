export function parseDomainToValues(rawDomain, rawContext) {
	// 1. Parse domain JSON/string → JS array
	let domain = [];
	if (typeof rawDomain === "string") {
		try {
			domain = JSON.parse(rawDomain.replace(/'/g, '"'));
		} catch {
			domain = [];
		}
	} else if (Array.isArray(rawDomain)) {
		domain = rawDomain;
	}

	// 2. Flatten out any leading '&'
	let clauses = [];
	if (Array.isArray(domain)) {
		if (domain[0] === "&") {
			clauses = domain.slice(1);
		} else {
			clauses = domain;
		}
	}

	// 3. Initialize value holder
	const v = {
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
		absMin: null,
		absMax: null,
	};

	// 4. Fill in from each clause
	clauses.forEach(([field, op, val]) => {
		switch (field) {
			case "province_id":
			case "district_id":
			case "commune_id":
			case "region_id":
			case "status_id":
			case "type_id":
			case "land_title_id":
				v[field] = String(val);
				break;
			case "feature_ids":
				if (op === "in" && Array.isArray(val)) {
					v.feature_ids = val.map((x) => String(x));
				}
				break;
			case "absolute_price":
				if (op === ">=") v.absMin = val;
				if (op === "<=") v.absMax = val;
				break;
		}
	});

	// 5. Parse context JSON/string → JS object
	let ctx = rawContext || {};
	if (typeof ctx === "string") {
		try {
			ctx = JSON.parse(ctx.replace(/'/g, '"'));
		} catch {
			ctx = {};
		}
	}

	// 6. Override price fields from context
	v.min_price = ctx.min_price || "";
	v.max_price = ctx.max_price || "";
	v.unit_price_min_id = ctx.unit_price_min_id || "";
	v.unit_price_max_id = ctx.unit_price_max_id || "";

	return v;
}

export function buildDomainFromValues(states, options) {
	const idOf = (v) => parseInt(v, 10) || null;
	const domain = [];

	// 1) Simple equality filters
	const simpleFields = [
		"province_id",
		"district_id",
		"commune_id",
		"region_id",
		"status_id",
		"type_id",
		"land_title_id",
	];
	simpleFields.forEach((field) => {
		const val = idOf(states[field]);
		if (val !== null) domain.push([field, "=", val]);
	});

	// 2) Multi-select
	if (Array.isArray(states.feature_ids) && states.feature_ids.length) {
		domain.push(["feature_ids", "in", states.feature_ids.map(idOf)]);
	}

	// 3) Price unit multiplier lookup
	const fetchMultiplier = (unitId) => {
		const uid = idOf(unitId);
		if (!uid) return 1;
		const unit = options.unit_prices.find((u) => u.id === uid);
		return unit?.multiplier || 1;
	};

	// 4) Absolute-price filters (new fields take priority)
	const { absMin, absMax } = states;
	if (absMin != null || absMax != null) {
		if (absMin != null) domain.push(["absolute_price", ">=", absMin]);
		if (absMax != null) domain.push(["absolute_price", "<=", absMax]);
	} else {
		// fallback to min_price/max_price + unit multipliers
		const minP = parseFloat(states.min_price);
		const maxP = parseFloat(states.max_price);

		if (!isNaN(minP))
			domain.push([
				"absolute_price",
				">=",
				minP * fetchMultiplier(states.unit_price_min_id),
			]);
		if (!isNaN(maxP))
			domain.push([
				"absolute_price",
				"<=",
				maxP * fetchMultiplier(states.unit_price_max_id),
			]);
	}

	return domain;
}
