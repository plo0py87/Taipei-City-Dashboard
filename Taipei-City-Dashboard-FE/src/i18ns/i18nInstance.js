import { createI18n } from "vue-i18n";
import zhBar from "./bars/zh.json";
import zhDialog from "./dialog/zh.json";
import enBar from "./bars/en.json";
import enDialog from "./dialog/en.json";
import zhMisc from "./misc/zh.json";
const messages = {
	zh: {
		...zhBar,
		dialog: zhDialog,
		...zhMisc,
	},
	en: {
		...enBar,
		dialog: enDialog,
	},
};

const instance = createI18n({
	locale: "zh", // Default locale
	fallbackLocale: "zh", // Fallback to default if translation not found
	messages,
});

export default instance;
export const i18n = instance.global;
