import js from '@eslint/js';
import ts from 'typescript-eslint';
export default ts.config(js.configs.recommended, ...ts.configs.recommended, {
  files: ['src/**/*.ts', 'src/**/*.tsx'],
  rules: {'@typescript-eslint/no-explicit-any':'error', '@typescript-eslint/no-unused-vars':'error'},
});
