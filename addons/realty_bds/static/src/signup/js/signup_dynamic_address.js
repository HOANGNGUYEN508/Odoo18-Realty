import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.SignupForm = publicWidget.Widget.extend({
	selector: ".oe_signup_form",
	events: {
		"change #province_id": "_onProvinceChange",
		"change #district_id": "_onDistrictChange",
		"change #province_resident_id": "_onProvinceResidentChange",
		"change #district_resident_id": "_onDistrictResidentChange",
	},

	/**
	 * Handle province selection change event
	 */
	_onProvinceChange: async function (ev) {
		let provinceId = ev.currentTarget.value;
		let districtSelect = document.querySelector("#district_id");

		if (!districtSelect) {
			console.error("❌ District selector not found!");
			return;
		}

		districtSelect.innerHTML =
			'<option value="" selected>Select District</option>';

		try {
			let result = await rpc("/get_districts", { province_id: provinceId });
			if (result.districts.length === 0) {
				console.warn("⚠️ No districts found for Province ID:", provinceId);
			} else {
				result.districts.forEach((d) => {
					let option = document.createElement("option");
					option.value = d.id;
					option.textContent = d.name;
					districtSelect.appendChild(option);
				});
			}
		} catch (err) {
			console.error("❌ Error fetching districts:", err);
		}
	},

	/**
	 * Handle district selection change event
	 */
	_onDistrictChange: async function (ev) {
		let districtId = ev.currentTarget.value;
		let communeSelect = document.querySelector("#commune_id");

		if (!communeSelect) {
			console.error("❌ Commune selector not found!");
			return;
		}

		communeSelect.innerHTML =
			'<option value="" selected>Select Commune</option>';

		try {
			let result = await rpc("/get_communes", { district_id: districtId });
			if (result.communes.length === 0) {
				console.warn("⚠️ No communes found for District ID:", districtId);
			} else {
				result.communes.forEach((c) => {
					let option = document.createElement("option");
					option.value = c.id;
					option.textContent = c.name;
					communeSelect.appendChild(option);
				});
			}
		} catch (err) {
			console.error("❌ Error fetching communes:", err);
		}
	},

	/**
	 * Handle province resident selection change event
	 */
	_onProvinceResidentChange: async function (ev) {
		let province_residentId = ev.currentTarget.value;
		let district_residentSelect = document.querySelector(
			"#district_resident_id"
		);

		if (!district_residentSelect) {
			console.error("❌ District selector not found!");
			return;
		}

		district_residentSelect.innerHTML =
			'<option value="" selected>Select District</option>';

		try {
			let result = await rpc("/get_districts", {
				province_id: province_residentId,
			});
			if (result.districts.length === 0) {
				console.warn(
					"⚠️ No districts found for Province ID:",
					province_residentId
				);
			} else {
				result.districts.forEach((d) => {
					let option = document.createElement("option");
					option.value = d.id;
					option.textContent = d.name;
					district_residentSelect.appendChild(option);
				});
			}
		} catch (err) {
			console.error("❌ Error fetching districts:", err);
		}
	},

	/**
	 * Handle district resident selection change event
	 */
	_onDistrictResidentChange: async function (ev) {
		let district_residentId = ev.currentTarget.value;
		let commune_residentSelect = document.querySelector("#commune_resident_id");

		if (!commune_residentSelect) {
			console.error("❌ Commune selector not found!");
			return;
		}

		commune_residentSelect.innerHTML =
			'<option value="" selected>Select Commune</option>';

		try {
			let result = await rpc("/get_communes", {
				district_id: district_residentId,
			});
			if (result.communes.length === 0) {
				console.warn(
					"⚠️ No communes found for District ID:",
					district_residentId
				);
			} else {
				result.communes.forEach((c) => {
					let option = document.createElement("option");
					option.value = c.id;
					option.textContent = c.name;
					commune_residentSelect.appendChild(option);
				});
			}
		} catch (err) {
			console.error("❌ Error fetching communes:", err);
		}
	},
});
