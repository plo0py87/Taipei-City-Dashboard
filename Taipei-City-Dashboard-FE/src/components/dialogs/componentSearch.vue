<!-- Developed by Taipei Urban Intelligence Center 2023-2024-->

<script setup>
import { ref, nextTick, onMounted } from "vue";
import { useChatStore } from "../../store/chatStore";

const chatStore = useChatStore();
const newMessage = ref("");
const messagesContainer = ref(null);

const sendMessage = async () => {
	if (newMessage.value.trim()) {
		chatStore.addMessage({
			text: newMessage.value,
			sender: "user",
			timestamp: new Date().toLocaleTimeString(),
		});
		newMessage.value = "";

		// 滾動到最新訊息
		await nextTick();
		if (messagesContainer.value) {
			messagesContainer.value.scrollTop =
				messagesContainer.value.scrollHeight;
		}
	}
};

// 處理關閉動畫
const handleClose = () => {
	const chatBox = document.querySelector(".chatBOX");
	const shadow = document.querySelector(".chat-shadow");

	if (chatBox && shadow) {
		chatBox.classList.add("closing");
		shadow.classList.add("closing");

		setTimeout(() => {
			chatStore.toggleModal();
		}, 300); // 等待動畫完成
	} else {
		chatStore.toggleModal();
	}
};
</script>

<template>
	<Transition name="modal" appear>
		<div class="chat-shadow" @click="handleClose" />
	</Transition>

	<Transition name="chatbox" appear>
		<div class="chatBOX">
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
						placeholder="輸入您的訊息..."
						@keyup.enter="sendMessage"
					/>
					<button
						class="send-button"
						@click="sendMessage"
						:disabled="!newMessage.trim()"
					>
						發送
					</button>
				</div>
			</div>
		</div>
	</Transition>
</template>

<style scoped>
/* 模態框淡入淡出動畫 */
.modal-enter-active,
.modal-leave-active {
	transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
	opacity: 0;
}

/* 聊天框彈出動畫 */
.chatbox-enter-active {
	transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.chatbox-leave-active {
	transition: all 0.3s cubic-bezier(0.55, 0.055, 0.675, 0.19);
}

.chatbox-enter-from {
	opacity: 0;
	transform: translate(-50%, -50%) scale(0.7) rotateX(30deg);
}

.chatbox-leave-to {
	opacity: 0;
	transform: translate(-50%, -50%) scale(0.9);
}

/* 新訊息淡入動畫 */
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

/* 基本樣式 */
.chat-shadow {
	position: fixed;
	top: 0;
	left: 0;
	width: 100vw;
	height: 100vh;
	background-color: rgba(0, 0, 0, 0.5);
	z-index: 9998;
	cursor: pointer;
	backdrop-filter: blur(2px);
	transition: backdrop-filter 0.3s ease;
}

.chat-shadow.closing {
	backdrop-filter: blur(0px);
}

.chatBOX {
	position: fixed;
	top: 50%;
	left: 50%;
	transform: translate(-50%, -50%);
	width: 66.67vw;
	height: 66.67vh;
	background-color: #f8f9fa;
	border-radius: 16px;
	box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 8px 30px rgba(0, 0, 0, 0.1);
	overflow: hidden;
	z-index: 9999;
	border: 1px solid rgba(255, 255, 255, 0.2);
}

.chatBOX.closing {
	animation: chatboxClose 0.3s cubic-bezier(0.55, 0.055, 0.675, 0.19) forwards;
}

@keyframes chatboxClose {
	to {
		opacity: 0;
		transform: translate(-50%, -50%) scale(0.9);
	}
}

.chat-container {
	display: flex;
	flex-direction: column;
	height: 100%;
	background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
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

/* 自定義滾動條 */
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

/* 響應式設計 */
@media (max-width: 768px) {
	.chatBOX {
		width: 90vw;
		height: 80vh;
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

/* 載入動畫 */
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
