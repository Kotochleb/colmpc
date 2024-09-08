///////////////////////////////////////////////////////////////////////////////
// BSD 3-Clause License
//
// Copyright (C) 2021, University of Edinburgh
// Copyright note valid unless otherwise stated in individual files.
// All rights reserved.
///////////////////////////////////////////////////////////////////////////////

#ifndef COLMPC_RESIDUAL_VELOCITY_AVOIDANCE_HPP_
#define COLMPC_RESIDUAL_VELOCITY_AVOIDANCE_HPP_

#include "colmpc/fwd.hpp"
// include fwd first

#include <hpp/fcl/collision_data.h>
#include <hpp/fcl/distance.h>

#include <Eigen/Core>
#include <crocoddyl/core/residual-base.hpp>
#include <crocoddyl/multibody/data/multibody.hpp>
#include <crocoddyl/multibody/fwd.hpp>
#include <crocoddyl/multibody/states/multibody.hpp>
#include <pinocchio/algorithm/frames-derivatives.hpp>
#include <pinocchio/algorithm/frames.hpp>
#include <pinocchio/algorithm/geometry.hpp>
#include <pinocchio/algorithm/jacobian.hpp>
#include <pinocchio/multibody/fcl.hpp>

#include "crocoddyl/core/utils/exception.hpp"

namespace colmpc {
using namespace crocoddyl;

template <typename _Scalar>
struct ResidualModelVelocityAvoidanceTpl
    : public ResidualModelAbstractTpl<_Scalar> {
  EIGEN_MAKE_ALIGNED_OPERATOR_NEW

  typedef _Scalar Scalar;
  typedef MathBaseTpl<Scalar> MathBase;
  typedef ResidualModelAbstractTpl<Scalar> Base;
  typedef ResidualDataDistanceCollisionTpl<Scalar> Data;
  typedef ResidualDataAbstractTpl<Scalar> ResidualDataAbstract;
  typedef StateMultibodyTpl<Scalar> StateMultibody;
  typedef DataCollectorAbstractTpl<Scalar> DataCollectorAbstract;
  typedef pinocchio::GeometryModel GeometryModel;
  typedef typename MathBase::VectorXs VectorXs;
  typedef typename MathBase::MatrixXs MatrixXs;
  typedef typename MathBase::Matrix6xs Matrix6xs;
  typedef typename MathBase::Vector3s Vector3s;
  typedef typename MathBase::Matrix<Scalar, 1, 3> RowVector3s;
  /**
   * @brief Initialize the pair collision residual model
   *
   * @param[in] state       State of the multibody system
   * @param[in] nu          Dimension of the control vector
   * @param[in] geom_model  Pinocchio geometry model containing the collision
   * pair
   * @param[in] pair_id     Index of the collision pair in the geometry model
   */

  ResidualModelVelocityAvoidanceTpl(boost::shared_ptr<StateMultibody> state,
                                    const std::size_t nu,
                                    boost::shared_ptr<GeometryModel> geom_model,
                                    const pinocchio::PairIndex pair_id);
  virtual ~ResidualModelVelocityAvoidanceTpl();

  /**
   * @brief Compute the pair collision residual
   *
   * @param[in] data  Pair collision residual data
   * @param[in] x     State point \f$\mathbf{x}\in\mathbb{R}^{ndx}\f$
   * @param[in] u     Control input \f$\mathbf{u}\in\mathbb{R}^{nu}\f$
   */
  virtual void calc(const boost::shared_ptr<ResidualDataAbstract> &data,
                    const Eigen::Ref<const VectorXs> &x,
                    const Eigen::Ref<const VectorXs> &u);

  /**
   * @brief Compute the derivatives of the pair collision residual
   *
   * @param[in] data  Pair collision residual data
   * @param[in] x     State point \f$\mathbf{x}\in\mathbb{R}^{ndx}\f$
   * @param[in] u     Control input \f$\mathbf{u}\in\mathbb{R}^{nu}\f$
   */
  virtual void calcDiff(const boost::shared_ptr<ResidualDataAbstract> &data,
                        const Eigen::Ref<const VectorXs> &x,
                        const Eigen::Ref<const VectorXs> &u);

  virtual boost::shared_ptr<ResidualDataAbstract> createData(
      DataCollectorAbstract *const data);

  /**
   * @brief Return the Pinocchio geometry model
   */
  const pinocchio::GeometryModel &get_geometry() const;

  /**
   * @brief Return the reference collision pair id
   */
  pinocchio::PairIndex get_pair_id() const;

  /**
   * @brief Modify the reference collision pair id
   */
  void set_pair_id(const pinocchio::PairIndex pair_id);

 protected:
  using Base::nu_;
  using Base::state_;
  using Base::unone_;
  using Base::v_dependent_;

 private:
  typename StateMultibody::PinocchioModel
      pin_model_;  //!< Pinocchio model used for internal computations
  boost::shared_ptr<pinocchio::GeometryModel>
      geom_model_;  //!< Pinocchio geometry model containing collision pair
  pinocchio::PairIndex
      pair_id_;  //!< Index of the collision pair in geometry model
  pinocchio::JointIndex joint_id_;  //!< Index of joint on which the collision
                                    //!< body frame of the robot is attached
};

template <typename _Scalar>
struct ResidualDataVelocityAvoidanceTpl
    : public ResidualDataAbstractTpl<_Scalar> {
  EIGEN_MAKE_ALIGNED_OPERATOR_NEW

  typedef _Scalar Scalar;
  typedef MathBaseTpl<Scalar> MathBase;
  typedef ResidualDataAbstractTpl<Scalar> Base;
  typedef StateMultibodyTpl<Scalar> StateMultibody;
  typedef DataCollectorAbstractTpl<Scalar> DataCollectorAbstract;

  typedef pinocchio::ModelTpl<Scalar> PinocchioModel;
  typedef typename MathBase::VectorXs VectorXs;
  typedef typename MathBase::Matrix6xs Matrix6xs;
  typedef typename MathBase::Vector3s Vector3s;

  template <template <typename Scalar> class Model>
  ResidualDataVelocityAvoidanceTpl(Model<Scalar> *const model,
                                   DataCollectorAbstract *const data)
      : Base(model, data),
        pinocchio(d->pinocchio),
        geometry(pinocchio::GeometryData(model->get_geometry())),
        req(),
        res(),
        J1(6, model->get_state()->get_nv()),
        J2(6, model->get_state()->get_nv()) {
    // Check that proper shared data has been passed
    DataCollectorMultibodyTpl<Scalar> *d =
        dynamic_cast<DataCollectorMultibodyTpl<Scalar> *>(shared);
    if (d == NULL) {
      throw_pretty(
          "Invalid argument: the shared data should be derived from "
          "DataCollectorActMultibodyTpl");
    }
  }
  pinocchio::GeometryData geometry;             //!< Pinocchio geometry data
  boost::shared_ptr<PinocchioModel> pinocchio;  //!< Pinocchio data

  using Base::r;
  using Base::Ru;
  using Base::Rx;
  using Base::shared;

  hpp::fcl::DistanceRequest
      req;  //!< Distance Request from hppfcl,
            //!< used to compute the distance between shapes
  hpp::fcl::DistanceResult res;  //!< Distance Result from hppfcl

  pinocchio::SE3 oMg_id_1;
  pinocchio::SE3 oMg_id_2;
};

}  // namespace colmpc

/* --- Details -------------------------------------------------------------- */
/* --- Details -------------------------------------------------------------- */
/* --- Details -------------------------------------------------------------- */
#include "colmpc/residual-distance-collision.hxx"
#endif  // COLMPC_RESIDUAL_VELOCITY_AVOIDANCE_HPP_
