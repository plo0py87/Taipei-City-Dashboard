<!-- Developed by Taipei Urban Intelligence Center 2023-2024-->

<script setup>
import { ref, nextTick } from "vue";
import { useChatStore } from "../../store/chatStore";
import { useDialogStore } from "../../store/dialogStore";
import { useI18n } from "vue-i18n";
import DialogContainer from "./DialogContainer.vue";
import axios from "axios";
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
		try {
			const response = await axios.post(
				"http://localhost:8000/query",
				{
					prompt: newMessage.value,
				},
				{
					headers: {
						"Content-Type": "application/json",
						accept: "application/json",
					},
				}
			);
			console.log(response.data);
		} catch (error) {
			console.error("API request failed:", error);
			// Handle error appropriately
		}
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
	background: linear-gradient(135deg, #23272f 0%, #181a20 100%);
	border-radius: 12px;
	overflow: hidden;
	box-shadow: 0 4px 32px rgba(0, 0, 0, 0.7);
}

.chat-messages {
	flex: 1;
	overflow-y: auto;
	padding: 24px;
	scroll-behavior: smooth;
	background: transparent;
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
	background: linear-gradient(135deg, #2563eb 0%, #1e293b 100%);
	color: #f1f5f9;
	border-radius: 20px 20px 6px 20px;
	box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
}

.bot-message {
	align-self: flex-start;
}

.bot-message .message-content {
	background: linear-gradient(135deg, #23272f 0%, #23272f 100%);
	color: #e0e6ed;
	border-radius: 20px 20px 20px 6px;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
	border: 1px solid rgba(255, 255, 255, 0.04);
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
	box-shadow: 0 6px 16px rgba(37, 99, 235, 0.35);
}

.bot-message .message-content:hover {
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}

.message-time {
	font-size: 11px;
	color: #94a3b8;
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
	background: linear-gradient(135deg, #181a20 0%, #23272f 100%);
	border-top: 1px solid rgba(255, 255, 255, 0.06);
	gap: 12px;
	backdrop-filter: blur(10px);
}

.chat-input {
	flex: 1;
	padding: 14px 20px;
	border: 2px solid #23272f;
	border-radius: 25px;
	outline: none;
	font-size: 14px;
	transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	color: #f1f5f9;
	background: rgba(36, 41, 51, 0.95);
	backdrop-filter: blur(5px);
}

.chat-input:focus {
	border-color: #2563eb;
	box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
	transform: translateY(-1px);
	background: rgba(36, 41, 51, 1);
}

.chat-input::placeholder {
	color: #64748b;
	transition: color 0.3s ease;
}

.chat-input:focus::placeholder {
	color: #94a3b8;
}

.send-button {
	padding: 14px 28px;
	background: linear-gradient(135deg, #2563eb 0%, #1e293b 100%);
	color: #f1f5f9;
	border: none;
	border-radius: 25px;
	cursor: pointer;
	font-size: 14px;
	font-weight: 600;
	transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
	position: relative;
	overflow: hidden;
}

.send-button:not(:disabled):hover {
	background: linear-gradient(135deg, #1e40af 0%, #0f172a 100%);
	box-shadow: 0 6px 20px rgba(37, 99, 235, 0.35);
	transform: translateY(-2px);
}

.send-button:not(:disabled):active {
	transform: translateY(0);
	box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
}

.send-button:disabled {
	background: linear-gradient(135deg, #334155 0%, #1e293b 100%);
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
		rgba(255, 255, 255, 0.08),
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
	background: rgba(36, 41, 51, 0.2);
	border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb {
	background: linear-gradient(135deg, #2563eb, #1e293b);
	border-radius: 3px;
	transition: background 0.3s ease;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
	background: linear-gradient(135deg, #1e293b, #0f172a);
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
