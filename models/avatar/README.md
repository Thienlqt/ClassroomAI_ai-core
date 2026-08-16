# Teacher avatar model

The frontend loads `teacher.vrm` from `/assets/avatar/teacher.vrm`. The model file is
ignored by Git.

The tested default is VRoid Project's `AvatarSample_A`, the same preset downloaded by
Project AIRI's Stage Web build:

```bash
curl --location --fail --continue-at - \
  --output models/avatar/teacher.vrm \
  https://dist.ayaka.moe/vrm-models/VRoid-Hub/AvatarSample-A/AvatarSample_A.vrm
```

Verified local SHA-256:

```text
2a0ccd84880b03d7b65503d8b6287f7a97f3bb4fab70a5fd0a47b433c97827f5
```

This sample is not CC0. Read and comply with the current
[VRoid sample-model terms](https://vroid.pixiv.help/hc/en-us/articles/4402394424089-VRoidPreset-A-Z)
before redistribution. You may replace it with another VRM whose license permits your
intended use.
