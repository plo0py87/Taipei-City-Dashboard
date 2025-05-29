import { defineStore } from "pinia";

export const useChatStore = defineStore("chat", {
	state: () => ({
		messages: [],
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
