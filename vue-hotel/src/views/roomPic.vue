<template>
  <div class="roomPic">
    <img v-if="src" :src="src" alt="room">
  </div>
</template>
<script>
export default {
  name: 'roomPic',
  data() {
    return {
      src: this.$route.params.src || ''
    }
  }
}
</script>
<style scoped>
.roomPic {
  text-align: center;
}
.roomPic img {
  max-width: 100%;
}
</style>
