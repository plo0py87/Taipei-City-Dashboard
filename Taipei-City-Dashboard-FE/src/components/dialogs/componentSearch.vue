<!-- Developed by Taipei Urban Intelligence Center 2023-2024-->

<script setup>
import { ref, nextTick } from "vue";
import { useChatStore } from "../../store/chatStore";
import { useDialogStore } from "../../store/dialogStore";
import { useI18n } from "vue-i18n";
import DialogContainer from "./DialogContainer.vue";

const { t } = useI18n();
const chatStore = useChatStore();
const dialogStore = useDialogStore();
const newMessage = ref("");
const messagesContainer = ref(null);

const sendMessage = async () => {
	if (newMessage.value.trim()) {
		// Add message to store
		if (!chatStore.messages) {
			chatStore.messages = [];
		}

		chatStore.messages.push({
			text: newMessage.value,
			sender: "user",
			timestamp: new Date().toLocaleTimeString(),
		});

		newMessage.value = "";

		// Scroll to the latest message
		await nextTick();
		if (messagesContainer.value) {
			messagesContainer.value.scrollTop =
				messagesContainer.value.scrollHeight;
		}

		// Here you would typically handle the bot response
		// Simulating a bot response after a short delay
		setTimeout(() => {
			chatStore.messages.push({
				text: "This is a demo response. The actual implementation would connect to your backend service.",
				sender: "bot",
				timestamp: new Date().toLocaleTimeString(),
			});

			// Scroll to the new message
			nextTick(() => {
				if (messagesContainer.value) {
					messagesContainer.value.scrollTop =
						messagesContainer.value.scrollHeight;
				}
			});
		}, 1000);
	}
};

// Handle the dialog close event
const handleClose = () => {
	dialogStore.hideAllDialogs();
};
</script>

<template>
	<DialogContainer dialog="NLPDialog" @on-close="handleClose">
		<div class="chat-container">
			<div ref="messagesContainer" class="chat-messages">
				<TransitionGroup
					name="message"
					tag="div"
					class="messages-wrapper"
				>
					<div
						v-for="(message, index) in chatStore.messages"
						:key="`${message.timestamp}-${index}`"
						:class="[
							'message',
							message.sender === 'user'
								? 'user-message'
								: 'bot-message',
						]"
					>
						<div class="message-content">
							{{ message.text }}
						</div>
						<div class="message-time">
							{{ message.timestamp }}
						</div>
					</div>
				</TransitionGroup>
			</div>
			<div class="chat-input-container">
				<input
					v-model="newMessage"
					class="chat-input"
					type="text"
					:placeholder="$t('dialog.輸入您的訊息...')"
					@keyup.enter="sendMessage"
				/>
				<button
					:disabled="!newMessage.trim()"
					class="send-button"
					@click="sendMessage"
				>
					{{ $t("dialog.發送") }}
				</button>
			</div>
		</div>
	</DialogContainer>
</template>

<style scoped>
/* Message animations */
.message-enter-active {
	transition: all 0.4s ease;
}

.message-leave-active {
	transition: all 0.3s ease;
}

.message-enter-from {
	opacity: 0;
	transform: translateY(20px) scale(0.95);
}

.message-leave-to {
	opacity: 0;
	transform: translateY(-10px) scale(0.95);
}

.message-move {
	transition: transform 0.3s ease;
}

/* Chat container styles */
.chat-container {
	display: flex;
	flex-direction: column;
	height: 70vh;
	width: 60vw;
	background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
	border-radius: 12px;
	overflow: hidden;
}

.chat-messages {
	flex: 1;
	overflow-y: auto;
	padding: 24px;
	scroll-behavior: smooth;
}

.messages-wrapper {
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.message {
	display: flex;
	flex-direction: column;
	max-width: 75%;
	animation: messageSlideIn 0.3s ease-out;
}

@keyframes messageSlideIn {
	from {
		opacity: 0;
		transform: translateY(15px);
	}
	to {
		opacity: 1;
		transform: translateY(0);
	}
}

.user-message {
	align-self: flex-end;
}

.user-message .message-content {
	background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
	color: white;
	border-radius: 20px 20px 6px 20px;
	box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
}

.bot-message {
	align-self: flex-start;
}

.bot-message .message-content {
	background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
	color: #2c3e50;
	border-radius: 20px 20px 20px 6px;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	border: 1px solid rgba(0, 0, 0, 0.05);
}

.message-content {
	padding: 14px 18px;
	word-wrap: break-word;
	font-size: 14px;
	line-height: 1.5;
	position: relative;
	transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.message-content:hover {
	transform: translateY(-1px);
}

.user-message .message-content:hover {
	box-shadow: 0 6px 16px rgba(0, 123, 255, 0.4);
}

.bot-message .message-content:hover {
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.message-time {
	font-size: 11px;
	color: #6c757d;
	margin-top: 6px;
	padding: 0 10px;
	opacity: 0.8;
	transition: opacity 0.2s ease;
}

.message:hover .message-time {
	opacity: 1;
}

.user-message .message-time {
	text-align: right;
}

.chat-input-container {
	display: flex;
	padding: 20px;
	background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
	border-top: 1px solid rgba(0, 0, 0, 0.08);
	gap: 12px;
	backdrop-filter: blur(10px);
}

.chat-input {
	flex: 1;
	padding: 14px 20px;
	border: 2px solid #e9ecef;
	border-radius: 25px;
	outline: none;
	font-size: 14px;
	transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	color: #2c3e50;
	background: rgba(255, 255, 255, 0.9);
	backdrop-filter: blur(5px);
}

.chat-input:focus {
	border-color: #007bff;
	box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
	transform: translateY(-1px);
	background: rgba(255, 255, 255, 1);
}

.chat-input::placeholder {
	color: #6c757d;
	transition: color 0.3s ease;
}

.chat-input:focus::placeholder {
	color: #adb5bd;
}

.send-button {
	padding: 14px 28px;
	background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
	color: white;
	border: none;
	border-radius: 25px;
	cursor: pointer;
	font-size: 14px;
	font-weight: 600;
	transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
	position: relative;
	overflow: hidden;
}

.send-button:not(:disabled):hover {
	background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
	box-shadow: 0 6px 20px rgba(0, 123, 255, 0.4);
	transform: translateY(-2px);
}

.send-button:not(:disabled):active {
	transform: translateY(0);
	box-shadow: 0 2px 8px rgba(0, 123, 255, 0.3);
}

.send-button:disabled {
	background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
	cursor: not-allowed;
	box-shadow: none;
	opacity: 0.6;
}

.send-button::before {
	content: "";
	position: absolute;
	top: 0;
	left: -100%;
	width: 100%;
	height: 100%;
	background: linear-gradient(
		90deg,
		transparent,
		rgba(255, 255, 255, 0.2),
		transparent
	);
	transition: left 0.5s ease;
}

.send-button:not(:disabled):hover::before {
	left: 100%;
}

/* Custom scrollbar */
.chat-messages::-webkit-scrollbar {
	width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
	background: rgba(0, 0, 0, 0.05);
	border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb {
	background: linear-gradient(135deg, #007bff, #0056b3);
	border-radius: 3px;
	transition: background 0.3s ease;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
	background: linear-gradient(135deg, #0056b3, #004085);
}

/* Responsive design */
@media (max-width: 768px) {
	.chat-container {
		width: 90vw;
		height: 70vh;
	}

	.message {
		max-width: 85%;
	}

	.chat-input-container {
		padding: 16px;
	}

	.send-button {
		padding: 12px 20px;
		font-size: 13px;
	}
}

/* Loading animation */
@keyframes pulse {
	0%,
	100% {
		opacity: 1;
	}
	50% {
		opacity: 0.5;
	}
}

.loading-message {
	animation: pulse 1.5s ease-in-out infinite;
}
</style>
