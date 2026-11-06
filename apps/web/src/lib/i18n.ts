/**
 * Türkçe arayüz için i18next yapılandırması.
 * Çeviri kaynaklarını React bileşenlerinin kullanımına açar.
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import admin from "../locales/tr/admin.json";
import auth from "../locales/tr/auth.json";
import common from "../locales/tr/common.json";
import test from "../locales/tr/test.json";
import dashboard from "../locales/tr/dashboard.json";
import landing from "../locales/tr/landing.json";

void i18n.use(initReactI18next).init({
  resources: {
    tr: {
      common,
      auth,
      admin,
      test,
      dashboard,
      landing,
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
