/**
 * web/static/js/main.esm.js
 * StoryBook Studio — Native ES Module Entrypoint & Web Component Registry
 * - Registers <storybook-dtp-spread> Custom Element
 * - Exposes structured ES Module namespace (window.StoryBookStudio) across the 5 domain modules
 * - Works both natively in FastAPI (/static/js/main.esm.js) and via Vite HMR / build
 */

import {
  DtpSpreadViewer,
  StorybookDtpSpreadElement,
  registerStorybookDtpSpreadComponent,
  mount as mountDtpSpread
} from "./components/storybook_dtp_spread.esm.js";

// Ensure <storybook-dtp-spread> Web Component is registered
registerStorybookDtpSpreadComponent();

/**
 * Structured ES Module Facade bridging the 5 Domain Modules & DTP Core
 */
export const StoryBookStudio = {
  version: "2.0.0-esm",
  components: {
    DtpSpreadViewer,
    StorybookDtpSpreadElement,
    mountDtpSpread,
  },
  get domainModules() {
    const w = typeof window !== "undefined" ? window : {};
    return {
      projectShelf: {
        openProjectBookModal: w.openProjectBookModal,
        switchProjectBook: w.switchProjectBook,
        createNewProjectBook: w.createNewProjectBook,
      },
      illustrationStudio: {
        generateCardPrompts: w.generateCardPrompts,
        selectDirectionCard: w.selectDirectionCard,
        generateIllustrationImage: w.generateIllustrationImage,
      },
      audioMusicStudio: {
        generateRecitationAudio: w.generateRecitationAudio,
        generateSongLyricsPrompt: w.generateSongLyricsPrompt,
        uploadSongMp3: w.uploadSongMp3,
      },
      thesaurusPalette: {
        openThesaurusModal: w.openThesaurusModal,
        filterThesaurusCategory: w.filterThesaurusCategory,
      },
      publishingExport: {
        exportBookkPdf: w.exportBookkPdf,
        exportCanvaPackage: w.exportCanvaPackage,
        openGalleryPreview: w.openGalleryPreview,
      },
      dtpEditor: w.dtpEditor || null,
    };
  },
};

if (typeof window !== "undefined") {
  window.StoryBookStudio = StoryBookStudio;
}

export { DtpSpreadViewer, StorybookDtpSpreadElement, mountDtpSpread };
export default StoryBookStudio;

