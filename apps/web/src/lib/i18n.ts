/**
 * Türkçe arayüz için i18next yapılandırması.
 * Çeviri kaynaklarını React bileşenlerinin kullanımına açar.
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import common from "../locales/tr/common.json";

void i18n.use(initReactI18next).init({
  resources: {
    tr: {
      common,
    },
  },
  lng: "tr",
  fallbackLng: "tr",
  defaultNS: "common",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
