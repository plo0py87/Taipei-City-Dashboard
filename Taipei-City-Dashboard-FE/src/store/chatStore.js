import { defineStore } from "pinia";

export const useChatStore = defineStore("chat", {
	state: () => ({
		messages: ["輸入你想知道的資訊，讓我幫你做個專屬的儀表板！"],
	}),
	actions: {
		addMessage(message) {
			this.messages.push(message);
		},

		clearMessages() {
			this.messages = [];
		},
	},
});
