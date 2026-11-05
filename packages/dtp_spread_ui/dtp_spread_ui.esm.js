/**
 * packages/dtp_spread_ui/dtp_spread_ui.esm.js
 * Native ES Module + W3C Web Component (<storybook-dtp-spread>)
 */
import "./dtp_spread_ui.js";

const DtpSpreadViewer = typeof window !== "undefined" && window.DtpSpreadUI
  ? window.DtpSpreadUI.DtpSpreadViewer
  : null;

const StorybookDtpSpreadElement = typeof window !== "undefined"
  ? window.StorybookDtpSpreadElement
  : null;

const mount = typeof window !== "undefined" && window.DtpSpreadUI
  ? window.DtpSpreadUI.mount
  : null;

export { DtpSpreadViewer, StorybookDtpSpreadElement, mount };
export default { DtpSpreadViewer, StorybookDtpSpreadElement, mount };

