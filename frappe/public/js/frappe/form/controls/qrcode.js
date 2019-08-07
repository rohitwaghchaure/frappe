import QRCode from 'qrcode/build/qrcode'


frappe.ui.form.ControlQrcode = frappe.ui.form.ControlData.extend({
	make_wrapper() {
		// Create the elements for qrcode area
		this._super();

		let $input_wrapper = this.$wrapper.find('.control-input-wrapper');
		this.qrcode_area = $(`<div class="qrcode-wrapper border"></div>`);
		this.qrcode_area.appendTo($input_wrapper);
	},

	parse(value) {
		// Parse raw value
		if(value) {
			return this.get_qrcode_html(value);
		}
	},

	set_formatted_input(value) {
		// Set values to display
		if (!value) {
			return
		}

		let svg = value;
		const qrcode_value = $(svg).attr('data-qrcode-value');

		if (!qrcode_value) { 
			this.get_qrcode_html(value).then(svg => {
				this.set_qrcode_value(svg, qrcode_value || value);
				this.doc[this.df.fieldname] = svg;
			})
		} else {
			this.set_qrcode_value(svg, qrcode_value);
		}
	},

	set_qrcode_value(svg, value) {
		this.$input.val(value);
		this.qrcode_area.html(svg);
	},

	get_qrcode_html(value) {
		// Get svg
		this.qrcode_area.empty();

		var opts = {
			type: 'String',
			rendererOpts: {
				scale: 1
			}
		}

		return new Promise((resolve) => {
			QRCode.toString(value, opts, (err, string) => {
				string = $(string).attr('data-qrcode-value', value);
				this.qrcode_area.append(string);
				resolve(this.qrcode_area.html());
			});
		});
	},
})