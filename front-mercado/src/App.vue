<script setup lang="ts">
import ToastHost from '@/components/ui/ToastHost.vue'
import ConfirmHost from '@/components/ui/ConfirmHost.vue'
import OfflineBanner from '@/components/ui/OfflineBanner.vue'
</script>

<template>
  <RouterView />
  <ToastHost />
  <ConfirmHost />
  <OfflineBanner />
</template>
