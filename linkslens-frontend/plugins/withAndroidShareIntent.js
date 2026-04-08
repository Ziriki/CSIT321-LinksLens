const { withMainActivity } = require("@expo/config-plugins");
const { mergeContents } = require("@expo/config-plugins/build/utils/generateCode");

/**
 * Config plugin that intercepts Android ACTION_SEND intents (share sheet) and
 * converts them into a linkslens:// deep link so Expo's Linking API can handle
 * them the same way as a normal URL open.
 *
 * Flow:
 *   User shares URL from browser
 *     → Android ACTION_SEND intent (EXTRA_TEXT = URL)
 *     → handleSendIntent() rewrites it to linkslens://scan?url=<encoded>
 *     → Expo Linking picks it up
 *     → _layout.tsx routes to /scan-link with the URL pre-filled
 */
module.exports = function withAndroidShareIntent(config) {
  return withMainActivity(config, (mod) => {
    if (mod.modResults.language !== "kt") return mod;

    // 1. Imports
    let result = mergeContents({
      src: mod.modResults.contents,
      anchor: /^import android\.os\.Bundle/m,
      offset: 1,
      comment: "//",
      tag: "withAndroidShareIntent-imports",
      newSrc: [
        "import android.content.Intent",
        "import android.net.Uri",
      ].join("\n"),
    });

    // 2. onNewIntent + handleSendIntent (inserted before invokeDefaultOnBackPressed)
    result = mergeContents({
      src: result.contents,
      anchor: /override fun invokeDefaultOnBackPressed\(\)/,
      offset: 0,
      comment: "//",
      tag: "withAndroidShareIntent-methods",
      newSrc: `
  override fun onNewIntent(intent: Intent) {
    handleSendIntent(intent)
    super.onNewIntent(intent)
  }

  private fun handleSendIntent(intent: Intent?) {
    intent ?: return
    if (intent.action == Intent.ACTION_SEND && intent.type?.startsWith("text/") == true) {
      val text = intent.getStringExtra(Intent.EXTRA_TEXT) ?: return
      val encoded = Uri.encode(text)
      intent.action = Intent.ACTION_VIEW
      intent.data = Uri.parse("linkslens://scan?url=${"$"}encoded")
    }
  }

`,
    });

    // 3. Call handleSendIntent in onCreate so cold-starts are handled too
    result = mergeContents({
      src: result.contents,
      anchor: /super\.onCreate\(null\)/,
      offset: 1,
      comment: "//",
      tag: "withAndroidShareIntent-oncreate",
      newSrc: "    handleSendIntent(intent)",
    });

    mod.modResults.contents = result.contents;
    return mod;
  });
};
