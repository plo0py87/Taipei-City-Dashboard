import { createI18n } from "vue-i18n";
import zhBar from "./bars/zh.json";
import zhDialog from "./dialog/zh.json";

const i18n = createI18n({
	locale: "zh",
	fallbackLocale: "zh",
	messages: {
		zh: {
			...zhBar,
			dialog: zhDialog,
		},
		en: null,
	},
});

export default i18n;
