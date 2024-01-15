'''
Example script : MPC simulation with KUKA arm 
static target reaching task
'''
from os.path import dirname, join, abspath

import pinocchio as pin
import hppfcl
import numpy as np
np.set_printoptions(precision=4, linewidth=180)

import pin_utils, mpc_utils
from mim_robots.pybullet.wrapper import PinBulletWrapper

RED = np.array([249, 136, 126, 125]) / 255
import pybullet

def load_pinocchio_robot_panda(capsule = False):
    """Load the robot from the models folder.

    Returns:
        rmodel, vmodel, cmodel: Robot model, visual model & collision model of the robot.
    """

    ### LOADING THE ROBOT
    pinocchio_model_dir = join(
        dirname(dirname(dirname(dirname(str(abspath(__file__)))))), "models"
    )
    model_path = join(pinocchio_model_dir, "franka_description/robots")
    mesh_dir = pinocchio_model_dir
    urdf_filename = "franka2.urdf"
    urdf_model_path = join(join(model_path, "panda"), urdf_filename)

    robot = pin.RobotWrapper.BuildFromURDF(
        urdf_model_path, mesh_dir, pin.JointModelFreeFlyer()
    )
    rmodel, [vmodel, cmodel] = robot.model, [robot.visual_model, robot.collision_model]
    q0 = pin.neutral(rmodel)

    rmodel, [vmodel, cmodel] = pin.buildReducedModel(
        rmodel, [vmodel, cmodel], [1, 9, 10], q0
    )
    cmodel_copy = cmodel.copy()
    list_names_capsules = []
    if capsule:
        for geometry_object in cmodel_copy.geometryObjects:
            if isinstance(geometry_object.geometry, hppfcl.Sphere):
                cmodel.removeGeometryObject(geometry_object.name)
            # Only selecting the cylinders
            if isinstance(geometry_object.geometry, hppfcl.Cylinder):
                if (geometry_object.name[:-4] + "capsule") in list_names_capsules:
                    capsule = pin.GeometryObject(
                    geometry_object.name[:-4] + "capsule" + "1",
                    geometry_object.parentJoint,
                    geometry_object.parentFrame,
                    geometry_object.placement,
                    hppfcl.Capsule(geometry_object.geometry.radius, geometry_object.geometry.halfLength),
                    )
                    capsule.meshColor = RED
                    cmodel.addGeometryObject(capsule)
                    cmodel.removeGeometryObject(geometry_object.name)
                    list_names_capsules.append(geometry_object.name[:-4] + "capsule" + "1" )
                else:
                    capsule = pin.GeometryObject(
                    geometry_object.name[:-4] + "capsule",
                    geometry_object.parentJoint,
                    geometry_object.parentFrame,
                    geometry_object.placement,
                    hppfcl.Capsule(geometry_object.geometry.radius, geometry_object.geometry.halfLength),
                    )
                    capsule.meshColor = RED
                    cmodel.addGeometryObject(capsule)
                    cmodel.removeGeometryObject(geometry_object.name)
                    list_names_capsules.append(geometry_object.name[:-4] + "capsule")

        
    ### CREATING THE SPHERE ON THE UNIVERSE
    OBSTACLE_RADIUS = 1.0e-1
    # OBSTACLE_POSE = pin.SE3.Identity()
    # OBSTACLE_POSE.translation = np.array([0.25, -0.425, 1.5])
    OBSTACLE_POSE = pin.SE3(pin.utils.rotate("x", np.pi), np.array([0, -0.2, 1.5]))
    OBSTACLE = hppfcl.Sphere(OBSTACLE_RADIUS)
    OBSTACLE_GEOM_OBJECT = pin.GeometryObject(
        "obstacle",
        rmodel.getFrameId("universe"),
        rmodel.frames[rmodel.getFrameId("universe")].parentJoint,
        OBSTACLE,
        OBSTACLE_POSE,
    )
    ID_OBSTACLE = cmodel.addGeometryObject(OBSTACLE_GEOM_OBJECT)

    # ### CREATING THE SPHERE ON THE END EFFECTOR
    # SPHERE2_RADIUS = 1.5e-1
    # SPHERE2_POSE = pin.SE3.Identity()
    # SPHERE2_POSE.translation = np.array([0.2, 0.0, 0.0])
    # SPHERE2 = hppfcl.Sphere(SPHERE2_RADIUS)
    # SPHERE2_GEOM_OBJECT = pin.GeometryObject(
    #     "SPHERE2",
    #     rmodel.getFrameId("panda2_leftfinger"),
    #     rmodel.frames[rmodel.getFrameId("panda2_leftfinger")].parentJoint,
    #     SPHERE2,
    #     SPHERE2_POSE,
    # )
    # ID_SPHERE2 = cmodel.addGeometryObject(SPHERE2_GEOM_OBJECT)

    # ### CREATING THE SPHERE ON THE ROBOT
    # SPHERE3_RADIUS = 1.5e-1
    # SPHERE3_POSE = pin.SE3.Identity()
    # SPHERE3_POSE.translation = np.array([0.0, 0.1, 0.2])
    # SPHERE3 = hppfcl.Sphere(SPHERE3_RADIUS)
    # SPHERE3_GEOM_OBJECT = pin.GeometryObject(
    #     "SPHERE3",
    #     rmodel.getFrameId("panda2_link3_sc_joint"),
    #     rmodel.frames[rmodel.getFrameId("panda2_link3_sc_joint")].parentJoint,
    #     SPHERE3,
    #     SPHERE3_POSE,
    # )
    # ID_SPHERE3 = cmodel.addGeometryObject(SPHERE3_GEOM_OBJECT)

    robot_reduced = pin.robot_wrapper.RobotWrapper(rmodel, cmodel, vmodel)  

    return robot_reduced


class PandaRobot(PinBulletWrapper):
    '''
    Pinocchio-PyBullet wrapper class for the KUKA LWR iiwa 
    '''
    def __init__(self, qref=np.zeros(7), pos=None, orn=None): 

        # Load the robot
        if pos is None:
            pos = [0.0, 0, 0.0]
        if orn is None:
            orn = pybullet.getQuaternionFromEuler([0, 0, 0])

        pinocchio_model_dir = join(
            dirname(dirname(dirname(dirname(str(abspath(__file__)))))), "models"
        )
        print(pinocchio_model_dir)
        model_path = join(pinocchio_model_dir, "franka_description/robots")
        mesh_dir = pinocchio_model_dir
        urdf_filename = "franka2.urdf"
        urdf_model_path = join(join(model_path, "panda"), urdf_filename)

        self.urdf_path = urdf_model_path
        self.robotId = pybullet.loadURDF(
            self.urdf_path,
            pos, orn,
            # flags=pybullet.URDF_USE_INERTIA_FROM_FILE,
            useFixedBase=True)
        pybullet.getBasePositionAndOrientation(self.robotId)
        
        # Create the robot wrapper in pinocchio.
        robot_full = load_pinocchio_robot_panda(capsule=False)

        
        # Query all the joints.
        num_joints = pybullet.getNumJoints(self.robotId)

        for ji in range(num_joints):
            pybullet.changeDynamics(self.robotId, 
                                    ji, 
                                    linearDamping=.04,
                                    angularDamping=0.04, 
                                    restitution=0.0, 
                                    lateralFriction=0.5)
          

        self.pin_robot = robot_full
        controlled_joints_names = ["panda2_joint1", "panda2_joint2", "panda2_joint3", "panda2_joint4", 
                                   "panda2_joint5", "panda2_joint6", "panda2_joint7"]
        
        self.base_link_name = "support_joint"
        self.end_eff_ids = []
        self.end_eff_ids.append(self.pin_robot.model.getFrameId('panda2_rightfinger'))
        self.nb_ee = len(self.end_eff_ids)
        self.joint_names = controlled_joints_names

        # Creates the wrapper by calling the super.__init__.          
        super(PandaRobot, self).__init__(
            self.robotId, 
            self.pin_robot,
            controlled_joints_names,
            ['panda2_finger_joint1'],
            useFixedBase=True)
        self.nb_dof = self.nv
        
    def forward_robot(self, q=None, dq=None):
        if q is None:
            q, dq = self.get_state()
        elif dq is None:
            raise ValueError("Need to provide q and dq or non of them.")

        self.pin_robot.forwardKinematics(q, dq)
        self.pin_robot.computeJointJacobians(q)
        self.pin_robot.framesForwardKinematics(q)
        self.pin_robot.centroidalMomentum(q, dq)

    def start_recording(self, file_name):
        self.file_name = file_name
        pybullet.startStateLogging(pybullet.STATE_LOGGING_VIDEO_MP4, self.file_name)

    def stop_recording(self):
        pybullet.stopStateLogging(pybullet.STATE_LOGGING_VIDEO_MP4, self.file_name)
        
        
