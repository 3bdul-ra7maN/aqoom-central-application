# مواصفة تشغيل بناء حزمة المستودع عبر Google Colab

## هوية المستودع
- المشروع: aqoom-central-application
- Project ID: 02
- المستودع الحالي: `3bdul-ra7maN/aqoom-central-application`
- المستودع المستهدف للتسليم: `3bdul-ra7maN/aqoom-central-application`
- التخصص: التطبيق المركزي للتنفيذ

## قاعدة المسؤولية
المشروع يحدد **ما الذي يدخل الحزمة** ويثبت مصدره وسبب إدخاله.
نظام التشغيل يحدد **كيف يتم الجمع والتحقق والتغليف والتسليم**.

ممنوع اختراع:
- ملفات مطلوبة
- مسارات
- إصدارات
- نتائج
- SHA256
- حالات نجاح

عند غياب أي معلومة لازمة تسجل: **MISSING DATA**.

## المسار التنفيذي
Request → Execution Specification → Colab → Collection → Manifest → SHA256 → Package → Verification → Delivery → Record Update

## خلايا Colab
| الخلية | الوظيفة | المخرج المتوقع |
|---|---|---|
| 00 | تعريف التنفيذ | Project ID / Execution ID / Package ID |
| 01 | ربط التخزين | مسار عمل ثابت وقابل للكتابة |
| 02 | تحميل Manifest | Manifest صالح |
| 03 | فحص المصدر | تقرير وجود الملفات ومطابقة المصدر |
| 04 | التجميع المرحلي | staging قابل للتتبع |
| 05 | إنشاء Manifest | source_manifest.json |
| 06 | حساب SHA256 | sha256_manifest.json |
| 07 | إنشاء الحزمة | ZIP |
| 08 | التحقق بعد البناء | verification_report.json |
| 09 | حفظ الحالة | execution_state.json |
| 10 | التسليم | DELIVERED أو BLOCKED موثق |
| 11 | تحديث السجل | حدث نهائي قابل للتتبع |

## قاعدة التتبع
Package File → Source File → Source Location → Verification

ولا تستخدم VERIFIED إلا بعد:
1. وجود الملف فعليًا.
2. نسخه إلى staging.
3. حساب SHA256 للمصدر.
4. حساب SHA256 للنسخة.
5. إثبات التطابق.
6. التحقق من الملف بعد استخراج الحزمة.

## الاستئناف
عند انقطاع Colab:
1. اقرأ execution_state.json.
2. استخدم last_completed_step وlast_completed_file.
3. افحص المخرجات السابقة.
4. لا تعِد خطوة ثبت نجاحها إلا إذا تغير المصدر.
5. استأنف من أول خطوة غير مكتملة.

## الحالات
FOUND، COPIED، VERIFIED، HASH-MATCH، PACKAGED، DELIVERED، UNVERIFIED

وحالات التنفيذ:
PREPARED، RUNNING، FAILED، RECOVERABLE، VERIFIED، DELIVERED، BLOCKED، CLOSED

## ما يجب على المشروع تعبئته قبل التشغيل
في Manifest:
- Package ID
- Name
- Version
- Files Required
- Source of Each File
- Target Repository
- Required Verification

عند كون files فارغة: الحالة **MISSING DATA** ولا يبدأ الجمع النهائي.

## ملاحظة المستودع الرابع
المسجل حاليًا هو `3bdul-ra7maN/-`.
الاسم المستهدف هو `3bdul-ra7maN/aqwam-guardian`.
لا تسجل إعادة التسمية كمكتملة قبل تحقق فعلي من GitHub.
