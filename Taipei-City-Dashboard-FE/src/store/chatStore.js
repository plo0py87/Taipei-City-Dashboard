import { defineStore } from "pinia";

export const useChatStore = defineStore("chat", {
	state: () => ({
		openModal: false,
	}),
	actions: {
		toggleModal() {
			this.openModal = !this.openModal;
		},
	},
});
