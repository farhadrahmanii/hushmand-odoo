/** @odoo-module **/
/**
 * The licence indicator in the systray.
 *
 * The gate refuses writes with an explanation, but only once somebody tries
 * to save something. This is the ambient half: a customer whose licence
 * lapses last Thursday should find that out from a badge in the corner, not
 * from a payroll clerk hitting a wall on the 28th.
 *
 * It renders nothing at all while the licence is healthy -- an indicator that
 * is always lit is an indicator nobody reads.
 */

import { Component, onWillStart, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

export class LicenceIndicator extends Component {
    static template = "hm_license.LicenceIndicator";
    static props = {};

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({ level: "off", message: "", canOpen: false });

        onWillStart(async () => {
            try {
                const status = await this.orm.call("hm.license", "status", [[]]);
                Object.assign(this.state, status);
                this.state.canOpen = await user.hasGroup("base.group_system");
            } catch {
                // A licence check that breaks the web client would be a far
                // worse bug than the one it is reporting. Stay quiet.
                this.state.level = "off";
            }
        });
    }

    get visible() {
        return this.state.level === "warning" || this.state.level === "danger";
    }

    get label() {
        return {
            missing: _t("No licence"),
            invalid: _t("Licence not valid"),
            expired: _t("Licence expired"),
            grace: _t("Licence lapsed"),
            expiring: _t("Licence expiring"),
            over_users: _t("Over user limit"),
        }[this.state.state] || _t("Licence");
    }

    openLicences() {
        if (this.state.canOpen) {
            this.action.doAction("hm_license.action_hm_license");
        }
    }
}

registry.category("systray").add(
    "hm_license.indicator",
    { Component: LicenceIndicator },
    { sequence: 40 }
);
