/** @odoo-module **/
/**
 * Gregorian <-> Jalaali conversion, formatting and parsing for the browser.
 *
 * This mirrors `core/jalali.py` and `core/formats.py` exactly -- the same
 * algorithm, the same month names, the same tokens. The Python side is the
 * authority; if you change one, change both and re-run the test suite, which
 * compares the two.
 */

const BREAKS = [
    -61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181,
    1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178,
];

// Truncate toward zero, matching the reference implementation. Using
// Math.floor here silently shifts dates in January and February.
const div = (a, b) => Math.trunc(a / b);
const mod = (a, b) => a - Math.trunc(a / b) * b;

export const SCHEME_AFGHAN = "afghan";
export const SCHEME_IRANIAN = "iranian";

export const MONTH_NAMES = {
    afghan: {
        en: ["Hamal", "Sawr", "Jawza", "Saratan", "Asad", "Sunbula",
             "Mizan", "Aqrab", "Qaws", "Jadi", "Dalwa", "Hoot"],
        fa: ["حمل", "ثور", "جوزا", "سرطان", "اسد", "سنبله",
             "میزان", "عقرب", "قوس", "جدی", "دلو", "حوت"],
        ps: ["وری", "غويی", "غبرګولی", "چنګاښ", "زمری", "وږی",
             "تله", "لړم", "لیندۍ", "مرغومی", "سلواغه", "کب"],
    },
    iranian: {
        en: ["Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar",
             "Mehr", "Aban", "Azar", "Dey", "Bahman", "Esfand"],
        fa: ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
             "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"],
    },
};

export const WEEKDAY_NAMES = {
    en: ["Shanbe", "Yakshanbe", "Doshanbe", "Seshanbe",
         "Chaharshanbe", "Panjshanbe", "Juma"],
    fa: ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"],
    ps: ["شنبه", "یکشنبه", "دوشنبه", "درېشنبه", "څلورشنبه", "پنجشنبه", "جمعه"],
};

const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";

export function toLatinDigits(text) {
    return String(text).replace(/[۰-۹٠-٩]/g, (ch) => {
        const p = PERSIAN_DIGITS.indexOf(ch);
        return String(p >= 0 ? p : ARABIC_DIGITS.indexOf(ch));
    });
}

export function toEasternDigits(text) {
    return String(text).replace(/[0-9]/g, (d) => PERSIAN_DIGITS[Number(d)]);
}

function jalCal(jy) {
    if (jy < BREAKS[0] || jy >= BREAKS[BREAKS.length - 1]) {
        throw new Error(`Jalaali year ${jy} is out of the supported range`);
    }
    const gy = jy + 621;
    let leapJ = -14;
    let jp = BREAKS[0];
    let jump = 1;

    for (let i = 1; i < BREAKS.length; i++) {
        const jm = BREAKS[i];
        jump = jm - jp;
        if (jy < jm) {
            break;
        }
        leapJ += div(jump, 33) * 8 + div(mod(jump, 33), 4);
        jp = jm;
    }

    let n = jy - jp;
    leapJ += div(n, 33) * 8 + div(mod(n, 33) + 3, 4);
    if (mod(jump, 33) === 4 && jump - n === 4) {
        leapJ += 1;
    }

    const leapG = div(gy, 4) - div((div(gy, 100) + 1) * 3, 4) - 150;
    const march = 20 + leapJ - leapG;

    if (jump - n < 6) {
        n = n - jump + div(jump + 4, 33) * 33;
    }
    let leap = mod(mod(n + 1, 33) - 1, 4);
    if (leap === -1) {
        leap = 4;
    }
    return { leap, gy, march };
}

function g2d(gy, gm, gd) {
    let d =
        div((gy + div(gm - 8, 6) + 100100) * 1461, 4) +
        div(153 * mod(gm + 9, 12) + 2, 5) +
        gd -
        34840408;
    d = d - div(div(gy + 100100 + div(gm - 8, 6), 100) * 3, 4) + 752;
    return d;
}

function d2g(jdn) {
    let j = 4 * jdn + 139361631;
    j = j + div(div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908;
    const i = div(mod(j, 1461), 4) * 5 + 308;
    const gd = div(mod(i, 153), 5) + 1;
    const gm = mod(div(i, 153), 12) + 1;
    const gy = div(j, 1461) - 100100 + div(8 - gm, 6);
    return { gy, gm, gd };
}

function j2d(jy, jm, jd) {
    const r = jalCal(jy);
    return g2d(r.gy, 3, r.march) + (jm - 1) * 31 - div(jm, 7) * (jm - 7) + jd - 1;
}

function d2j(jdn) {
    const gy = d2g(jdn).gy;
    let jy = gy - 621;
    const r = jalCal(jy);
    const jdn1F = g2d(gy, 3, r.march);
    let k = jdn - jdn1F;

    if (k >= 0) {
        if (k <= 185) {
            return { jy, jm: 1 + div(k, 31), jd: mod(k, 31) + 1 };
        }
        k -= 186;
    } else {
        jy -= 1;
        k += 179;
        if (r.leap === 1) {
            k += 1;
        }
    }
    return { jy, jm: 7 + div(k, 30), jd: mod(k, 30) + 1 };
}

export function toJalali(gy, gm, gd) {
    return d2j(g2d(gy, gm, gd));
}

export function toGregorian(jy, jm, jd) {
    return d2g(j2d(jy, jm, jd));
}

export function isLeapJalaliYear(jy) {
    return jalCal(jy).leap === 0;
}

export function jalaliMonthLength(jy, jm) {
    if (jm <= 6) {
        return 31;
    }
    if (jm <= 11) {
        return 30;
    }
    return isLeapJalaliYear(jy) ? 30 : 29;
}

export function isValidJalali(jy, jm, jd) {
    return (
        jy >= -61 && jy <= 3177 &&
        jm >= 1 && jm <= 12 &&
        jd >= 1 && jd <= jalaliMonthLength(jy, jm)
    );
}

function monthNames(scheme, lang) {
    const bySchema = MONTH_NAMES[scheme] || MONTH_NAMES.afghan;
    return bySchema[lang] || (lang === "ps" && bySchema.fa) || bySchema.en;
}

function weekdayNames(lang) {
    return WEEKDAY_NAMES[lang] || WEEKDAY_NAMES.en;
}

/** Index in the Saturday-first Afghan week. JS getDay(): Sunday is 0. */
function weekdayIndex(jsDate) {
    return (jsDate.getDay() + 1) % 7;
}

const TOKEN_RE = /yyyy|yy|MMMM|MMM|MM|M|dd|d|EEEE|EEE|HH|H|mm|ss/g;

// Text between single quotes is literal, so "'Issued on' dd/MM/yyyy" does not
// lose the "ss" and "d" out of the word "Issued". Two quotes mean one quote.
const QUOTED_RE = /'((?:[^']|'')*)'/g;

const pad = (n) => String(n).padStart(2, "0");

/**
 * Format a plain object `{year, month, day, hour, minute, second}` as Jalali.
 * Accepts anything with those properties, which covers both a luxon DateTime
 * and a hand-built object -- deliberately, so this file has no luxon import.
 */
export function formatJalali(value, options = {}) {
    if (!value) {
        return "";
    }
    const {
        format = "yyyy/MM/dd",
        scheme = SCHEME_AFGHAN,
        lang = "en",
        easternDigits = false,
    } = options;

    const { jy, jm, jd } = toJalali(value.year, value.month, value.day);
    const months = monthNames(scheme, lang);
    const jsDate = new Date(value.year, value.month - 1, value.day);

    const substitute = (fragment) => fragment.replace(TOKEN_RE, (token) => {
        switch (token) {
            case "yyyy": return String(jy).padStart(4, "0");
            case "yy": return pad(jy % 100);
            case "MMMM": return months[jm - 1];
            case "MMM": return months[jm - 1].slice(0, 3);
            case "MM": return pad(jm);
            case "M": return String(jm);
            case "dd": return pad(jd);
            case "d": return String(jd);
            case "EEEE": return weekdayNames(lang)[weekdayIndex(jsDate)];
            case "EEE": return weekdayNames(lang)[weekdayIndex(jsDate)].slice(0, 3);
            case "HH": return pad(value.hour || 0);
            case "H": return String(value.hour || 0);
            case "mm": return pad(value.minute || 0);
            case "ss": return pad(value.second || 0);
            default: return token;
        }
    });

    // Substitute tokens only outside quoted literals.
    const pieces = [];
    let position = 0;
    QUOTED_RE.lastIndex = 0;
    let quoted;
    while ((quoted = QUOTED_RE.exec(format)) !== null) {
        pieces.push(substitute(format.slice(position, quoted.index)));
        pieces.push(quoted[1].replace(/''/g, "'"));
        position = quoted.index + quoted[0].length;
    }
    pieces.push(substitute(format.slice(position)));

    const out = pieces.join("");
    return easternDigits ? toEasternDigits(out) : out;
}

function monthFromName(token) {
    const needle = token.trim().toLowerCase();
    for (const scheme of Object.values(MONTH_NAMES)) {
        for (const names of Object.values(scheme)) {
            const index = names.findIndex((n) => {
                const lowered = n.toLowerCase();
                return lowered === needle || lowered.startsWith(needle);
            });
            if (index !== -1) {
                return index + 1;
            }
        }
    }
    return null;
}

/**
 * Parse Jalali text into a Gregorian `{year, month, day}`.
 * Returns null when the text is not a valid Jalali date.
 */
export function parseJalali(text) {
    if (!text) {
        return null;
    }
    const parts = toLatinDigits(String(text).trim())
        .split(/[/\-.\s،]+/)
        .filter(Boolean);
    if (parts.length < 3) {
        return null;
    }

    const numbers = [];
    let namedMonth = null;
    for (const part of parts.slice(0, 4)) {
        if (/^\d+$/.test(part)) {
            numbers.push(Number(part));
        } else {
            const resolved = monthFromName(part);
            if (resolved === null) {
                return null;
            }
            namedMonth = resolved;
        }
    }

    let jy;
    let jm;
    let jd;
    if (namedMonth !== null) {
        if (numbers.length < 2) {
            return null;
        }
        jm = namedMonth;
        if (numbers[0] > 31) {
            [jy, jd] = numbers;
        } else {
            [jd, jy] = numbers;
        }
    } else {
        if (numbers.length < 3) {
            return null;
        }
        [jy, jm, jd] = numbers;
    }

    if (jy < 100) {
        const current = toJalali(
            new Date().getFullYear(),
            new Date().getMonth() + 1,
            new Date().getDate()
        ).jy;
        jy = Math.trunc(current / 100) * 100 + jy;
    }

    if (!isValidJalali(jy, jm, jd)) {
        return null;
    }
    const g = toGregorian(jy, jm, jd);
    return { year: g.gy, month: g.gm, day: g.gd };
}
