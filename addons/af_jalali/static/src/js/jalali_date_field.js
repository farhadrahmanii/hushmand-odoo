/** @odoo-module **/
/**
 * TIER 2 -- the only version-sensitive file in this module.
 *
 * It is deliberately built on a plain <input> rather than Odoo's internal
 * DateTimePicker, because that picker is the part of the web client that
 * changes most between releases. Porting to a new Odoo version should mean
 * checking the four imports below and nothing else.
 */

import { Component, onWillStart, useState } from "@odoo/owl";
import { DateTime } from "luxon";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { formatJalali, parseJalali } from "./jalali";

const DEFAULTS = {
    enabled: true,
    scheme: "afghan",
    lang: "en",
    eastern_digits: false,
    date_format: "yyyy/MM/dd",
    datetime_format: "yyyy/MM/dd HH:mm",
};

/**
 * Fetches the company and user calendar settings once per session.
 * Returns defaults if the call fails, so a broken RPC degrades to a working
 * field rather than a blank form.
 */
export const jalaliSettingsService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        let pending = null;
        let cached = null;
        return {
            get settings() {
                return cached || DEFAULTS;
            },
            async load() {
                if (cached) {
                    return cached;
                }
                if (!pending) {
                    pending = orm
                        .call("af.jalali", "client_settings", [])
                        .then((result) => {
                            cached = { ...DEFAULTS, ...result };
                            return cached;
                        })
                        .catch(() => {
                            cached = DEFAULTS;
                            return cached;
                        });
                }
                return pending;
            },
        };
    },
};

registry.category("services").add("af_jalali", jalaliSettingsService);

export class JalaliDateField extends Component {
    static template = "af_jalali.JalaliDateField";
    static props = {
        ...standardFieldProps,
        withTime: { type: Boolean, optional: true },
        format: { type: String, optional: true },
    };

    setup() {
        this.jalali = useService("af_jalali");
        this.state = useState({ invalid: false });
        onWillStart(() => this.jalali.load());
    }

    get settings() {
        return this.jalali.settings;
    }

    get value() {
        return this.props.record.data[this.props.name] || false;
    }

    /** The Jalali text shown in the input. */
    get displayValue() {
        const value = this.value;
        if (!value) {
            return "";
        }
        return formatJalali(value, {
            format: this.props.format || this.pattern,
            scheme: this.settings.scheme,
            lang: this.settings.lang,
            easternDigits: this.settings.eastern_digits,
        });
    }

    get pattern() {
        return this.props.withTime
            ? this.settings.datetime_format
            : this.settings.date_format;
    }

    get placeholder() {
        return this.pattern.replace(/EEEE|EEE/g, "").trim();
    }

    get title() {
        // The Gregorian equivalent, so a user can always cross-check.
        const value = this.value;
        return value ? value.toFormat("yyyy-MM-dd") : "";
    }

    onChange(ev) {
        const text = ev.target.value.trim();

        if (!text) {
            this.state.invalid = false;
            this.props.record.update({ [this.props.name]: false });
            return;
        }

        const parsed = parseJalali(text);
        if (!parsed) {
            this.state.invalid = true;
            return;
        }
        this.state.invalid = false;

        const previous = this.value;
        const next = DateTime.fromObject({
            year: parsed.year,
            month: parsed.month,
            day: parsed.day,
            // Keep the time of day when editing a datetime field.
            hour: this.props.withTime && previous ? previous.hour : 0,
            minute: this.props.withTime && previous ? previous.minute : 0,
            second: 0,
        });

        this.props.record.update({ [this.props.name]: next });
    }

    onKeydown(ev) {
        if (ev.key === "Escape") {
            ev.target.value = this.displayValue;
            this.state.invalid = false;
        }
    }
}

export const jalaliDateField = {
    component: JalaliDateField,
    displayName: _t("Jalali Date"),
    supportedTypes: ["date", "datetime"],
    extractProps: ({ options, attrs }) => ({
        withTime: options.time === true,
        format: options.format || attrs?.format || undefined,
    }),
};

export const jalaliDatetimeField = {
    ...jalaliDateField,
    displayName: _t("Jalali Date & Time"),
    supportedTypes: ["datetime"],
    extractProps: ({ options, attrs }) => ({
        withTime: options.time !== false,
        format: options.format || attrs?.format || undefined,
    }),
};

registry.category("fields").add("jalali_date", jalaliDateField);
registry.category("fields").add("jalali_datetime", jalaliDatetimeField);
