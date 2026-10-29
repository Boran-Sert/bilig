/**
 * ESLint ayarları: TypeScript, JSDoc ve i18next kuralları.
 * shadcn/ui bileşenlerinde JSDoc zorunluluğu uygulanmaz.
 */
import js from "@eslint/js";
import { defineConfig } from "eslint/config";
import i18next from "eslint-plugin-i18next";
import jsdoc from "eslint-plugin-jsdoc";
import tseslint from "typescript-eslint";

export default defineConfig(
  { ignores: ["dist"] },
  js.configs.recommended,
  tseslint.configs.recommended,
  i18next.configs["flat/recommended"],
  {
    plugins: { jsdoc },
    rules: {
      "jsdoc/require-jsdoc": [
        "error",
        {
          require: {
            FunctionDeclaration: true,
            MethodDefinition: true,
            ClassDeclaration: true,
            ArrowFunctionExpression: true,
          },
        },
      ],
    },
  },
  {
    files: ["src/components/ui/**"],
    rules: {
      "jsdoc/require-jsdoc": "off",
    },
  },
);
