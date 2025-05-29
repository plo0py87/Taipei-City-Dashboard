<!-- Developed by Taipei Urban Intelligence Center 2023-2024-->

<script setup>
import { useDialogStore } from "../../store/dialogStore";
import { useI18n } from "vue-i18n";

import DialogContainer from "./DialogContainer.vue";

const dialogStore = useDialogStore();
const { t } = useI18n();

defineProps(["contributor"]);

function handleClose() {
	dialogStore.dialogs.contributorInfo = false;
}
</script>

<template>
	<DialogContainer :dialog="`contributorInfo`" @on-close="handleClose">
		<div class="contributorinfo">
			<div class="contributorinfo-img">
				<img
					:src="
						contributor.image.includes('http')
							? contributor.image
							: `/images/contributors/${contributor.image}`
					"
					:alt="`${$t('dialog.協作者')}-${contributor.user_name}`"
				/>
				<h2>{{ contributor.user_name }}</h2>
			</div>
			<div class="contributorinfo-info">
				<label>{{ $t("dialog.身份") }}</label>
				<p>
					{{ contributor.identity }}
				</p>
				<label>{{ $t("dialog.貢獻項目") }}</label>
				<p>{{ contributor.description }}</p>
				<a :href="contributor.link" target="_blank" rel="noreferrer"
					>{{
						contributor.link.includes("github")
							? "GitHub "
							: $t("dialog.相關")
					}}{{ $t("dialog.連結") }} <span>open_in_new</span></a
				>
			</div>
		</div>
	</DialogContainer>
</template>

<style scoped lang="scss">
.contributorinfo {
	width: 250px;
	display: flex;
	column-gap: 20px;
	align-items: center;

	&-img {
		min-width: 80px;
		display: flex;
		flex-direction: column;
		align-items: center;
		row-gap: 8px;

		h2 {
			text-align: center;
			font-weight: 400;
			font-size: var(--font-ms);
		}

		img {
			min-width: 80px;
			width: 80px;
			height: 80px;
			border-radius: 50%;
		}
	}

	&-info {
		display: flex;
		flex-direction: column;

		label {
			margin: 4px 0 0px;
			font-size: var(--font-s);
			color: var(--color-complement-text);
		}

		a {
			margin-top: 8px;
			color: var(--color-highlight);
			font-size: var(--font-s);
			display: flex;
			align-items: center;
			gap: 4px;

			span {
				color: var(--color-highlight);
				font-size: 16px;
				font-family: var(--font-icon);
			}
		}
	}
}
</style>
