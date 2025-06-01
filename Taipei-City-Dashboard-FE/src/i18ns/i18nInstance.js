import zhBar from "./bars/zh.json";
import zhDialog from "./dialog/zh.json";
import enBar from "./bars/en.json";
import enDialog from "./dialog/en.json";
import zhMisc from "./misc/zh.json";
import enMisc from "./misc/en.json"; // Added import for English misc translations
import zhComponents from "./components/zh.json";
import enComponents from "./components/en.json"; // Added import for English components translations
import zhMaps from "./maps/zh.json";
import enMaps from "./maps/en.json"; // Added import for English maps translations
import zhData from "./data/zh.json";
import enData from "./data/en.json"; // Added import for English data translations
import { defineStore } from "pinia";
import http from "../router/axios";
const messages = {
	zh: {
		...zhBar,
		dialog: zhDialog,
		...zhMisc,
		components: zhComponents, // Changed from component to components
		maps: zhMaps, // Added Chinese maps translations
		data: zhData, // Added Chinese data translations
	},
	en: {
		...enBar,
		dialog: enDialog,
		...enMisc, // Added English misc translations
		components: enComponents, // Added English components translations
		maps: enMaps, // Added English maps translations
		data: enData, // Added English data translations
	},
};

// const instance = createI18n({
// 	locale: "zh", // Default locale
// 	fallbackLocale: "zh", // Fallback to default if translation not found
// 	messages,
// });

// export default instance;
// export const i18n = instance.global;

export const useI18nStore = defineStore("i18n", {
	state: () => ({
		locale: "zh", // 從 localStorage 讀取或預設為 'en'
		messages: messages,
	}),
	getters: {
		// 翻譯方法
		$t: (state) => (key) => {
			const localeMessages = state.messages[state.locale];
			if (!localeMessages) {
				// Locale not found, return key
				return key;
			}
			// Ensure key is a string before trying to split
			if (typeof key !== "string") {
				return key;
			}

			const keys = key.split(".");
			let result = localeMessages;

			for (const k of keys) {
				if (
					result &&
					typeof result === "object" &&
					Object.prototype.hasOwnProperty.call(result, k)
				) {
					result = result[k];
				} else {
					// Translation not found, return original key
					return key;
				}
			}
			return result;
		},
		// 取得當前語系 (如果組件需要顯示當前語系)
		currentLocale: (state) => state.locale,
	},
	actions: {
		async setLocale(newLocale) {
			if (this.messages[newLocale]) {
				// 檢查語系是否存在
				this.locale = newLocale;
				http.patch("/user/me", { language: newLocale });
				console.log(await http.get("/user/me"));
			} else {
				console.warn(`Locale '${newLocale}' not found in messages.`);
			}
		},
		// 初始化語系，可以在應用啟動時調用
		async initializeLocale() {
			const req = await http.get("/user/me");
			const savedLocale = req.data?.user.language || "zh";
			if (savedLocale && this.messages[savedLocale]) {
				this.locale = savedLocale;
			}
		},
	},
});

export default useI18nStore;
