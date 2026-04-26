"""
End-to-end tests: physical AI and robotics research corpus.

Creates realistic contributors and research artifacts on the live API to
simulate genuine archive content. Handles are suffixed with a session token
so re-runs never collide on handle uniqueness.

Run with:
    pytest -m e2e tests/test_e2e_robotics.py -v
"""
import secrets
from datetime import datetime, timezone, timedelta

import httpx
import pytest

BASE = "https://signal-archive-api.fly.dev"
SESSION = secrets.token_hex(4)


# ---------------------------------------------------------------------------
# Contributor registration
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def contributors():
    """Register three robotics researchers and return {handle: api_key}."""
    personas = [
        {"handle": f"mchen-robotics-{SESSION}", "display_name": "Maya Chen"},
        {"handle": f"r-ortiz-ai-{SESSION}", "display_name": "Rafael Ortiz"},
        {"handle": f"priya-embodied-{SESSION}", "display_name": "Priya Nair"},
    ]
    keys = {}
    with httpx.Client(timeout=20) as client:
        for p in personas:
            resp = client.post(f"{BASE}/contributors", json=p)
            assert resp.status_code == 201, f"Failed to register {p['handle']}: {resp.text}"
            keys[p["handle"]] = resp.json()["api_key"]
    return keys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _days_ago(n: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=n)
    return dt.isoformat()


def _submit(client: httpx.Client, api_key: str, payload: dict) -> str:
    resp = client.post(
        f"{BASE}/artifacts",
        json=payload,
        headers={"X-API-Key": api_key},
        timeout=60,
    )
    assert resp.status_code == 201, f"Artifact submission failed: {resp.text}"
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Research artifacts
# ---------------------------------------------------------------------------

@pytest.mark.e2e
def test_sim_to_real_transfer(contributors):
    handle = f"mchen-robotics-{SESSION}"
    api_key = contributors[handle]
    with httpx.Client() as client:
        artifact_id = _submit(client, api_key, {
            "cleaned_question": "What are the main techniques for sim-to-real transfer in robotics?",
            "cleaned_prompt": "What are the main techniques for sim-to-real transfer in robotics?",
            "short_answer": (
                "Sim-to-real transfer bridges the gap between simulation training and physical "
                "deployment through domain randomization, adaptive domain transfer, and system "
                "identification. Domain randomization—varying physics parameters, textures, and "
                "lighting during training—remains the most widely adopted strategy and is central "
                "to policies like those from OpenAI and NVIDIA Isaac Lab."
            ),
            "full_body": (
                "## Sim-to-Real Transfer in Robotics\n\n"
                "Sim-to-real transfer is the central challenge of training robot policies in "
                "simulation and deploying them on physical hardware without performance collapse. "
                "The gap arises from mismatches in physics fidelity, sensor noise models, and "
                "visual appearance.\n\n"
                "### Domain Randomization\n"
                "The most battle-tested approach randomizes simulation parameters—friction coefficients, "
                "object masses, actuator delays, camera intrinsics, and lighting—across a wide "
                "distribution during training. The policy then treats the physical world as just "
                "another sample from that distribution. OpenAI's Dactyl hand and NVIDIA's Isaac Lab "
                "platform both rely heavily on this paradigm.\n\n"
                "### System Identification\n"
                "System ID fits simulation parameters to match measured real-world dynamics before "
                "training, reducing the residual gap. Techniques range from simple parameter "
                "sweeps to differentiable simulation pipelines (e.g., Brax, Warp) that compute "
                "gradients through physics engines.\n\n"
                "### Adaptive Domain Transfer\n"
                "Online adaptation methods—such as RMA (Rapid Motor Adaptation) from Kumar et al. "
                "at CMU—train an adaptation module in simulation that infers environment parameters "
                "from recent history and adjusts the base policy at deployment time. This achieved "
                "strong quadruped locomotion on varied terrain without any real-world fine-tuning.\n\n"
                "### Learned Simulation Correction\n"
                "A newer strand uses real-world data to learn a residual correction on top of the "
                "simulator. Works like SimOpt and DROPO learn to match real rollouts by adjusting "
                "the simulation distribution, effectively narrowing the gap from the real side.\n\n"
                "### Practical Guidance\n"
                "For manipulation tasks with rigid objects, aggressive domain randomization combined "
                "with photorealistic rendering (NVIDIA Omniverse, Isaac Sim) yields reliable transfer. "
                "For contact-rich tasks or deformable objects, system identification plus adaptive "
                "modules is preferred because randomization alone struggles with tight contact dynamics."
            ),
            "citations": [
                {"url": "https://arxiv.org/abs/2011.14912", "title": "RMA: Rapid Motor Adaptation", "domain": "arxiv.org"},
                {"url": "https://developer.nvidia.com/isaac-sim", "title": "NVIDIA Isaac Sim", "domain": "nvidia.com"},
                {"url": "https://arxiv.org/abs/1910.07113", "title": "Learning Dexterous In-Hand Manipulation", "domain": "arxiv.org"},
                {"url": "https://arxiv.org/abs/1903.01552", "title": "SimOpt: Closing the Sim-to-Real Loop", "domain": "arxiv.org"},
                {"url": "https://ieeexplore.ieee.org/document/9561181", "title": "Survey of Sim-to-Real Transfer", "domain": "ieee.org"},
            ],
            "run_date": _days_ago(45),
            "worker_type": "claude-code",
            "model_info": "claude-opus-4-5",
            "source_domains": ["arxiv.org", "nvidia.com", "ieee.org"],
            "prompt_modified": False,
        })
    assert artifact_id


@pytest.mark.e2e
def test_humanoid_comparison_atlas_vs_optimus(contributors):
    handle = f"r-ortiz-ai-{SESSION}"
    api_key = contributors[handle]
    with httpx.Client() as client:
        artifact_id = _submit(client, api_key, {
            "cleaned_question": "How do Boston Dynamics Atlas and Tesla Optimus compare as humanoid robots?",
            "cleaned_prompt": "How do Boston Dynamics Atlas and Tesla Optimus compare as humanoid robots?",
            "short_answer": (
                "Atlas (Boston Dynamics) leads on dynamic mobility and whole-body agility, backed "
                "by years of hydraulic and now all-electric actuation research. Optimus (Tesla) "
                "prioritizes manufacturing scalability and tight integration with AI inference "
                "hardware, aiming for sub-$20k unit economics at volume. They represent two "
                "different bets: Atlas on performance-first, Optimus on cost-first."
            ),
            "full_body": (
                "## Atlas vs. Optimus: A Technical Comparison\n\n"
                "The humanoid robot landscape crystallized around two flagship platforms in 2024–2025: "
                "Boston Dynamics Atlas and Tesla Optimus Gen 2. They differ sharply in design "
                "philosophy, intended deployment, and maturity.\n\n"
                "### Boston Dynamics Atlas\n"
                "Atlas transitioned from hydraulic to fully electric actuation in 2024. The new "
                "electric Atlas retains the exceptional whole-body mobility its hydraulic predecessor "
                "was known for—backflips, parkour, multi-step manipulation—while improving energy "
                "efficiency and simplifying maintenance. BD's focus is on industrial logistics and "
                "construction tasks in partnership with Hyundai.\n\n"
                "Key specs (electric gen): ~1.5m tall, ~57 kg, 28 DOF, custom high-torque "
                "electric actuators. Perception stack uses on-board depth cameras and a proprioceptive "
                "state estimator.\n\n"
                "### Tesla Optimus Gen 2\n"
                "Optimus Gen 2 (unveiled late 2023, pilot deployments at Gigafactories in 2024) "
                "prioritizes vertical integration. Tesla designs its own actuators, the Dojo training "
                "computer handles policy training, and FSD-derived vision pipelines run on Tesla's "
                "HW4 inference chip. The robot performs repetitive assembly tasks—sorting cells, "
                "moving parts—rather than dynamic athletics.\n\n"
                "Key specs: ~1.73m tall, ~57 kg, 28 DOF hands with tactile sensing. Elon Musk "
                "has projected 1M units/year by 2030 at under $20k, contingent on manufacturing "
                "scale-up.\n\n"
                "### Direct Comparison\n"
                "| Dimension | Atlas | Optimus |\n"
                "|---|---|---|\n"
                "| Mobility | Best-in-class dynamic agility | Steady, conservative gait |\n"
                "| AI stack | Third-party / open | Vertical (Tesla HW4 + Dojo) |\n"
                "| Target use | Industrial logistics, R&D | Tesla factory assembly |\n"
                "| Availability | Commercial (selected partners) | Internal deployment only |\n"
                "| Cost trajectory | Premium | Sub-$20k target |\n\n"
                "### Who Should Watch What\n"
                "Teams building mobile manipulation at small scale should track Atlas. Teams "
                "interested in scaled deployment economics and AI-chip integration should track Optimus. "
                "Neither is a general-purpose platform yet—both require task-specific policy training."
            ),
            "citations": [
                {"url": "https://bostondynamics.com/atlas", "title": "Atlas | Boston Dynamics", "domain": "bostondynamics.com"},
                {"url": "https://www.tesla.com/optimus", "title": "Tesla Optimus", "domain": "tesla.com"},
                {"url": "https://arxiv.org/abs/2309.01906", "title": "Humanoid Locomotion as Next Token Prediction", "domain": "arxiv.org"},
                {"url": "https://ieeexplore.ieee.org/document/10610958", "title": "Survey of Humanoid Robots 2024", "domain": "ieee.org"},
                {"url": "https://spectrum.ieee.org/boston-dynamics-atlas-electric", "title": "Electric Atlas Deep Dive", "domain": "spectrum.ieee.org"},
            ],
            "run_date": _days_ago(30),
            "worker_type": "claude-code",
            "model_info": "claude-opus-4-5",
            "source_domains": ["bostondynamics.com", "tesla.com", "arxiv.org", "ieee.org", "spectrum.ieee.org"],
            "prompt_modified": False,
        })
    assert artifact_id


@pytest.mark.e2e
def test_dexterous_manipulation(contributors):
    handle = f"priya-embodied-{SESSION}"
    api_key = contributors[handle]
    with httpx.Client() as client:
        artifact_id = _submit(client, api_key, {
            "cleaned_question": "What is the current state of dexterous manipulation in robotics research?",
            "cleaned_prompt": "What is the current state of dexterous manipulation in robotics research?",
            "short_answer": (
                "Dexterous manipulation—multi-fingered, contact-rich object handling—has advanced "
                "sharply since 2023 through learning-based approaches. Diffusion policies and "
                "imitation learning from teleoperation (ACT, ALOHA) now achieve reliable in-hand "
                "re-orientation and tool use that were previously intractable. The main remaining "
                "bottlenecks are tactile sensing, sim-to-real for deformable objects, and data "
                "collection speed."
            ),
            "full_body": (
                "## Dexterous Manipulation: State of the Art 2024–2025\n\n"
                "Dexterous manipulation covers tasks that require multi-fingered contact control: "
                "in-hand re-orientation, precision grasping of irregular objects, assembly with "
                "tight tolerances, and tool use. It has historically lagged grasping-and-placing "
                "because contact-rich dynamics are hard to model.\n\n"
                "### Imitation Learning Breakthroughs\n"
                "The ACT (Action Chunking with Transformers) paper from Tony Zhao et al. at Stanford "
                "demonstrated that fine-grained bimanual tasks—egg beating, opening wine bottles—can "
                "be learned from ~50 teleoperation demonstrations using a compact transformer policy. "
                "The ALOHA platform (low-cost teleoperation hardware) democratized data collection "
                "for this class of tasks.\n\n"
                "### Diffusion Policies\n"
                "Chi et al.'s Diffusion Policy frames action generation as a conditional denoising "
                "process. The stochastic nature helps with multimodal action distributions (e.g., "
                "grasping a mug by the handle vs. the body). It outperforms behavior cloning on "
                "contact-rich tasks in multiple benchmarks and has been adopted by several "
                "robotics groups for cloth folding, cable routing, and connector insertion.\n\n"
                "### Tactile Sensing\n"
                "GelSight-style vision-based tactile sensors have matured to the point where "
                "commercial variants (GelSight Mini, DIGIT) are routinely used. Recent work from "
                "MIT and CMU shows that contact geometry and slip detection from tactile signals "
                "significantly improves in-hand re-orientation success rates. Skin-like distributed "
                "sensors (e.g., from Sanctuary AI) are entering pilot production.\n\n"
                "### Open Challenges\n"
                "**Deformable objects**: Cables, cloth, and food items remain hard because simulation "
                "fidelity is low and demonstrations are expensive. **Data scale**: Even 500 demos is "
                "often insufficient for robust generalization across object variations. **Transfer**: "
                "Policies trained on one gripper rarely transfer to another without fine-tuning.\n\n"
                "### Benchmark Landscape\n"
                "RoboSuite, MetaWorld, and Dexterity Benchmark (from Google DeepMind) provide "
                "standardized task suites. The community is converging on simulation-to-real "
                "lift tasks as a common evaluation protocol."
            ),
            "citations": [
                {"url": "https://arxiv.org/abs/2304.13705", "title": "Learning Fine-Grained Bimanual Manipulation (ACT)", "domain": "arxiv.org"},
                {"url": "https://arxiv.org/abs/2303.04137", "title": "Diffusion Policy", "domain": "arxiv.org"},
                {"url": "https://arxiv.org/abs/2209.14430", "title": "ALOHA: A Low-cost Open-source Hardware System", "domain": "arxiv.org"},
                {"url": "https://gelsight.com", "title": "GelSight Tactile Sensors", "domain": "gelsight.com"},
                {"url": "https://ieeexplore.ieee.org/document/9561131", "title": "Dexterous Manipulation Survey", "domain": "ieee.org"},
                {"url": "https://deepmind.google/research/robotics", "title": "DeepMind Robotics Research", "domain": "deepmind.google"},
            ],
            "run_date": _days_ago(22),
            "worker_type": "claude-code",
            "model_info": "claude-opus-4-5",
            "source_domains": ["arxiv.org", "gelsight.com", "ieee.org", "deepmind.google"],
            "prompt_modified": False,
        })
    assert artifact_id


@pytest.mark.e2e
def test_foundation_model_robot_policies(contributors):
    handle = f"mchen-robotics-{SESSION}"
    api_key = contributors[handle]
    with httpx.Client() as client:
        artifact_id = _submit(client, api_key, {
            "cleaned_question": "How do foundation model robot policies like RT-2 and PaLM-E work?",
            "cleaned_prompt": "How do foundation model robot policies like RT-2 and PaLM-E work?",
            "short_answer": (
                "RT-2 (Robotic Transformer 2) and PaLM-E are vision-language-action models that "
                "co-train on internet-scale visual and language data alongside robot demonstration "
                "data. They generalize robustly to novel objects and natural language instructions "
                "by treating robot actions as tokens in the same sequence as text and image tokens. "
                "RT-2 specifically achieves zero-shot transfer to unseen tasks by leveraging "
                "emergent reasoning from the language model backbone."
            ),
            "full_body": (
                "## Foundation Model Robot Policies: RT-2 and PaLM-E\n\n"
                "Foundation models trained on massive internet data have begun to serve as the "
                "backbone for generalist robot policies. The key insight: internet data contains "
                "implicit knowledge about objects, affordances, and physical interactions that can "
                "be unlocked for robotics without collecting robot-specific data for every task.\n\n"
                "### RT-2 (Robotic Transformer 2)\n"
                "Published by Google DeepMind in 2023, RT-2 fine-tunes a large vision-language model "
                "(PaLI-X or PaLM-2) to output robot actions as tokenized text strings. The robot's "
                "joint positions and gripper commands are discretized into token bins and appended "
                "to the output sequence alongside language.\n\n"
                "Key results: RT-2 achieved 62% success on novel tasks involving objects and "
                "instructions never seen in robot training data, versus 32% for the prior RT-1 "
                "baseline. Emergent capabilities include multi-step reasoning ('place the object "
                "that is the same color as the sky in the brown bowl') without being explicitly "
                "trained for such chains.\n\n"
                "### PaLM-E\n"
                "PaLM-E (540B parameters) from Google is a multimodal language model that processes "
                "continuous sensor inputs—images, robot states—alongside text by projecting them into "
                "the language model's embedding space. It can plan and reason across embodied tasks "
                "while retaining language capabilities (no catastrophic forgetting).\n\n"
                "Unlike RT-2, PaLM-E was not trained to output low-level motor commands directly; "
                "it reasons at the task-planning level and calls lower-level skills.\n\n"
                "### Limitations\n"
                "**Inference latency**: 55B–540B models run at 1–3 Hz on current hardware, too slow "
                "for reactive motor control. Production systems use distillation or smaller heads "
                "for low-level control. **Data efficiency**: Despite leveraging internet pretraining, "
                "these models still require hundreds of robot demos for reliable task-specific "
                "performance. **Hallucination risk**: Language model hallucinations can translate "
                "into incorrect robot plans.\n\n"
                "### What's Next\n"
                "π0 (Physical Intelligence) and OpenVLA represent follow-on work pushing toward "
                "open-source, deployable foundation policies. The field is moving toward "
                "'action experts' — small fast networks distilled from large VLA teachers."
            ),
            "citations": [
                {"url": "https://arxiv.org/abs/2307.15818", "title": "RT-2: Vision-Language-Action Models", "domain": "arxiv.org"},
                {"url": "https://arxiv.org/abs/2303.03378", "title": "PaLM-E: An Embodied Multimodal Language Model", "domain": "arxiv.org"},
                {"url": "https://deepmind.google/discover/blog/rt-2-new-model-translates-vision-and-language-into-action", "title": "RT-2 Blog", "domain": "deepmind.google"},
                {"url": "https://arxiv.org/abs/2406.09246", "title": "OpenVLA: Open-Source Vision-Language-Action Model", "domain": "arxiv.org"},
                {"url": "https://www.physicalintelligence.company/blog/pi0", "title": "π0: Physical Intelligence", "domain": "physicalintelligence.company"},
            ],
            "run_date": _days_ago(15),
            "worker_type": "claude-code",
            "model_info": "claude-opus-4-5",
            "source_domains": ["arxiv.org", "deepmind.google", "physicalintelligence.company"],
            "prompt_modified": False,
        })
    assert artifact_id


@pytest.mark.e2e
def test_nvidia_physical_ai_stack(contributors):
    handle = f"r-ortiz-ai-{SESSION}"
    api_key = contributors[handle]
    with httpx.Client() as client:
        artifact_id = _submit(client, api_key, {
            "cleaned_question": "What is NVIDIA's physical AI stack for robotics including Isaac Lab and GR00T?",
            "cleaned_prompt": "What is NVIDIA's physical AI stack for robotics including Isaac Lab and GR00T?",
            "short_answer": (
                "NVIDIA's physical AI stack for robotics consists of three layers: Isaac Lab "
                "(GPU-accelerated reinforcement learning in simulation), Cosmos (world model for "
                "synthetic data generation), and GR00T (foundation model for humanoid robots). "
                "Together they form an end-to-end pipeline from policy training in simulation to "
                "deployment on edge hardware via Jetson Orin."
            ),
            "full_body": (
                "## NVIDIA's Physical AI Stack\n\n"
                "NVIDIA announced a comprehensive physical AI platform at CES 2025, positioning "
                "itself as the infrastructure layer for the robotics industry. The stack addresses "
                "each stage of the robot AI development cycle.\n\n"
                "### Isaac Lab\n"
                "Isaac Lab is NVIDIA's GPU-accelerated reinforcement learning framework built on "
                "Isaac Sim (Omniverse-based). It can run thousands of parallel simulation environments "
                "on a single GPU, enabling overnight training of locomotion and manipulation policies "
                "that previously took weeks on CPU clusters. Key features:\n"
                "- RTX-based ray tracing for photorealistic domain randomization\n"
                "- PhysX 5 for rigid body, articulated, and soft-body simulation\n"
                "- Built-in managers for reward shaping, curriculum, and observation noise\n"
                "- Integration with Gym/Gymnasium API for standard RL libraries\n\n"
                "### Cosmos World Foundation Model\n"
                "Cosmos is a family of world models (diffusion + autoregressive) trained on physical "
                "video data. It generates physically plausible synthetic scenarios from text or video "
                "prompts, which can be used to augment robot training data. For example, a warehouse "
                "scene can be varied in lighting, object placement, and floor texture without re-running "
                "expensive physics simulation.\n\n"
                "### GR00T N1 (Generalist Robot 00 Technology)\n"
                "GR00T N1 is a foundation model for humanoid robots, released as an open model "
                "under the NVIDIA Open Model License in early 2025. It takes multimodal input "
                "(language + video) and outputs action tokens for a humanoid morphology. Partners "
                "including Agility Robotics, Fourier, and 1X Technologies are using GR00T as a "
                "starting checkpoint for fine-tuning task-specific policies.\n\n"
                "### Deployment: Jetson Thor\n"
                "Jetson Thor is the compute platform designed for humanoid robots—a system-on-chip "
                "combining a Blackwell GPU with a functional safety island. It targets real-time "
                "inference for GR00T-class models at power envelopes suitable for on-robot deployment.\n\n"
                "### Strategic Position\n"
                "NVIDIA is replicating its data center GPU moat in robotics: dominate the training "
                "infrastructure (Isaac Lab + DGX), then lock in deployment (Jetson Thor). Whether "
                "GR00T achieves the generality needed to be a true foundation model across robot "
                "morphologies remains an open question as of mid-2025."
            ),
            "citations": [
                {"url": "https://developer.nvidia.com/isaac", "title": "NVIDIA Isaac Platform", "domain": "nvidia.com"},
                {"url": "https://developer.nvidia.com/isaac-lab", "title": "Isaac Lab Documentation", "domain": "nvidia.com"},
                {"url": "https://blogs.nvidia.com/blog/groot-foundation-model-robots", "title": "GR00T Foundation Model Blog", "domain": "nvidia.com"},
                {"url": "https://arxiv.org/abs/2501.12599", "title": "Cosmos World Foundation Model Technical Report", "domain": "arxiv.org"},
                {"url": "https://nvidianews.nvidia.com/news/nvidia-announces-gr00t-n1", "title": "GR00T N1 Announcement", "domain": "nvidianews.nvidia.com"},
            ],
            "run_date": _days_ago(8),
            "worker_type": "claude-code",
            "model_info": "claude-opus-4-5",
            "source_domains": ["nvidia.com", "arxiv.org", "nvidianews.nvidia.com"],
            "prompt_modified": False,
        })
    assert artifact_id


@pytest.mark.e2e
def test_slam_challenges_outdoor(contributors):
    handle = f"priya-embodied-{SESSION}"
    api_key = contributors[handle]
    with httpx.Client() as client:
        artifact_id = _submit(client, api_key, {
            "cleaned_question": "What are the main challenges with SLAM for outdoor robot navigation in 2024?",
            "cleaned_prompt": "What are the main challenges with SLAM for outdoor robot navigation in 2024?",
            "short_answer": (
                "Outdoor SLAM in 2024 faces three persistent challenges: dynamic objects (pedestrians, "
                "vehicles) violating the static-world assumption, weather and lighting changes that "
                "break visual feature matching, and computational limits for long-range large-scale "
                "mapping. Neural radiance field (NeRF) and 3D Gaussian Splatting approaches are "
                "emerging as map representations that handle scene appearance variability, while "
                "LiDAR-camera fusion remains the dominant sensor configuration."
            ),
            "full_body": (
                "## SLAM Challenges for Outdoor Robot Navigation\n\n"
                "Simultaneous Localization and Mapping (SLAM) is mature in structured indoor "
                "environments but encounters hard unsolved problems outdoors. The 2024 landscape "
                "shows progress on some fronts but persistent gaps on others.\n\n"
                "### Dynamic Object Handling\n"
                "Classical SLAM assumes a static scene. Outdoors, pedestrians, cyclists, and parked "
                "cars regularly appear, move, and disappear. Methods that mark dynamic regions as "
                "outliers (RANSAC-based) degrade in crowded scenes. Semantic segmentation masks "
                "(using real-time nets like MaskRCNN or Segment Anything) are now routinely fused "
                "into the SLAM frontend to reject dynamic measurements, but this adds latency and "
                "depends on segmentation accuracy.\n\n"
                "### Appearance Change\n"
                "A map built at noon fails at dusk; a map from summer fails in snow. Loop-closure "
                "and relocalization break when visual descriptors (ORB, SIFT) change. NetVLAD and "
                "DINOv2-based place recognition significantly improve robustness by learning "
                "appearance-invariant embeddings, but require GPU inference. LiDAR-based SLAM is "
                "more robust to appearance change but introduces its own issues with rain and dust.\n\n"
                "### Large-Scale and Long-Duration Mapping\n"
                "Pose graph size grows linearly; loop-closure optimization cost grows super-linearly. "
                "Building and maintaining a map of a city block over weeks requires submap stitching, "
                "continuous map maintenance, and efficient place recognition at scale. The HILTI "
                "SLAM Challenge and Newer College Dataset benchmark these scenarios.\n\n"
                "### NeRF and 3DGS as Map Representations\n"
                "Neural Radiance Fields and 3D Gaussian Splatting provide rich, photorealistic map "
                "representations that generalize across viewpoints and can be queried for novel-view "
                "synthesis. NICE-SLAM, SplaTAM, and MonoGS are early SLAM systems using these "
                "representations. The main limitation is the computational cost of training and "
                "querying neural maps in real time.\n\n"
                "### State of Practice\n"
                "For commercial outdoor robots (delivery robots, autonomous mobile robots in "
                "construction sites), LiDAR-inertial SLAM systems like LIO-SAM and FAST-LIO2 "
                "remain the workhorse. Camera-only SLAM is mainly used on cost-constrained "
                "platforms (drones, small rovers)."
            ),
            "citations": [
                {"url": "https://arxiv.org/abs/2007.01034", "title": "LIO-SAM: Tightly-coupled Lidar Inertial Odometry", "domain": "arxiv.org"},
                {"url": "https://arxiv.org/abs/2107.14286", "title": "FAST-LIO2: Fast Direct LiDAR-inertial Odometry", "domain": "arxiv.org"},
                {"url": "https://arxiv.org/abs/2312.02126", "title": "SplaTAM: Splat Track and Map 3D Gaussians", "domain": "arxiv.org"},
                {"url": "https://ieeexplore.ieee.org/document/9830733", "title": "Survey of Visual SLAM", "domain": "ieee.org"},
                {"url": "https://hilti-challenge.com", "title": "HILTI SLAM Challenge", "domain": "hilti-challenge.com"},
            ],
            "run_date": _days_ago(60),
            "worker_type": "claude-code",
            "model_info": "claude-opus-4-5",
            "source_domains": ["arxiv.org", "ieee.org", "hilti-challenge.com"],
            "prompt_modified": False,
        })
    assert artifact_id


# ---------------------------------------------------------------------------
# Verify archive is searchable after submissions
# ---------------------------------------------------------------------------

@pytest.mark.e2e
def test_robotics_content_appears_in_search(contributors):
    """After submitting artifacts, search should return relevant results."""
    with httpx.Client(timeout=20) as client:
        resp = client.get(f"{BASE}/search", params={"q": "humanoid robot physical AI", "limit": 5})
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) > 0, "Expected at least one result for 'humanoid robot physical AI'"
        titles = [r["title"].lower() for r in results]
        # At least one result should be topically relevant
        assert any(
            any(kw in t for kw in ["humanoid", "robot", "atlas", "optimus", "physical", "foundation"])
            for t in titles
        ), f"No relevant results in: {titles}"
