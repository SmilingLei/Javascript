<template>
  <section id="contact">
    <div class="container">
      <div class="row">
        <div class="col-md-12">
          <div class="inner contact">
            <!-- Form Area -->
            <div class="contact-form">
              <!-- Form -->
              <form id="contact-us" method="post" action="http://127.0.0.1:3000/api/api/addMessage">
                <!-- Left Inputs -->
                <div class="col-md-6 ">
                  <!-- Name -->
                  <input type="text" name="name" id="name" required="required" class="form" placeholder="subject">
                  <!-- Email -->
                  <input type="email" name="email" id="email" required="required" class="form" placeholder="Email">
                  <!-- Subject -->
                  <input type="text" name="subject" id="subject" required="required" class="form" placeholder="name">
                </div>
                <!-- End Left Inputs -->
                <!-- Right Inputs -->
                <div class="col-md-6">
                  <!-- Message -->
                  <textarea name="message" id="message" class="form textarea" placeholder="Message"></textarea>
                </div>
                <!-- End Right Inputs -->
                <!-- Bottom Submit -->
                <div class="relative fullwidth col-xs-12">
                  <!-- Send Button -->
                  <button type="submit" id="submit" class="form-btn">Send Message</button>
                </div>
                <!-- End Bottom Submit -->
                <!-- Clear -->
                <div class="clear"></div>
              </form>
            </div>
            <!-- End Contact Form Area -->
          </div>
          <!-- End Inner -->
        </div>
      </div>
    </div>
  </section>
</template>
<script>
export default {
  data() {

  }
}

</script>
