# Google AI Studio Prompt

اعمل على AQOOM Central Application MVP v0.1.

حافظ على Product Boundary والعقود والسلوك الحالي.

المسار:
Task → Assignment → Execution → Result → Evidence → T_accounted → RT → Settlement Record → Training Record → Trace

القاعدة:
1 RT = 30 ns
RT = T_accounted / 30ns

MVP لا يستنتج T_accounted من نوع الجهد.

Settlement في MVP يعني Settlement Record فقط، وليس دفعًا ماليًا.

Trainer في MVP يقرأ Training Data فقط.

المطلوب:
- واجهة عربية RTL حديثة.
- Dashboard.
- Requester Workspace.
- Executor Workspace.
- Execution Trace.
- Trainer Workspace.
- Demo Mode عند غياب Backend.
- API Mode عند توفر Backend.

لا تضف:
Payment Gateway
Revenue Engine
Marketplace
Automatic Matching
Autonomous Learning
Blockchain
Microservices

لا تغيّر Domain Rules لمجرد تحسين الواجهة.
