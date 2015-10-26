# -*- coding:utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy import and_
from sqlalchemy.orm import sessionmaker
import os
import uuid

from satree import TreeManager,TreeMixin

def get_uuid():
    return uuid.uuid4().hex


cur_path = os.path.abspath(os.path.dirname(__file__))
cur_db_file = os.path.join(cur_path, "test.db")

sqlite_uri = r'sqlite:///%s' % cur_db_file

engine = create_engine(sqlite_uri, echo=True)
Base = declarative_base()

session = sessionmaker(bind=engine)()


class User(Base, TreeMixin):
    __tablename__ = "user"
    __tree_output_fields__=["name","age"]
    id = Column(String(32), primary_key=True, default=get_uuid)
    name = Column(String(60), default="")
    age=Column(Integer,default=0)
    sex=Column(Integer,default=0)

    # TreeManager=TreeManager()

    @property
    def pk(self):
        """
            返回主关键字值,只返回一个主关键字
         """
        return self.__dict__[self.__table__.primary_key.columns.values()[0].name]


    def __repr__(self):
        return "User(%s)" % self.name

    @property
    def session(cls):
        return session



tm=TreeManager(User,session)


ACTION =1110
#node1 = session.query(User).filter(User.name == "2-A").one()
# node2 = session.query(User).filter(User.name == "B1").one()
#tm.batch_add_nodes([User(name="x1"),User(name="x2")],node1,pos=2)

#
ref_node1 = session.query(User).filter(User.name == "root1").one()
ref_node2 = session.query(User).filter(User.name == "root2").one()
print tm.output([ref_node1,ref_node2],format="json",flatted=False)


# print ref_node1.to_json()

tm.verify_tree(0)
tm.repair_tree(0)
if ACTION==0:


    Base.metadata.create_all(engine)
    root_node = User(name="root1")
    tm.add_node(root_node)

    child_node_a=User(name="A")
    tm.add_node(child_node_a,root_node)

    child_node_b=User(name="B")
    tm.add_node(child_node_b,root_node)
    child_node_b1=User(name="B1")
    tm.add_node(child_node_b1,child_node_b)
    # child_node_b2=User(name="B2")
    # tm.add_node(child_node_b2,child_node_b)

    child_node_c=User(name="C")
    tm.add_node(child_node_c,root_node)

    #增加子节点
    child_node=User(name="B1_1")
    tm.add_node(child_node,child_node_b1)
    child_node=User(name="B1_2")
    tm.add_node(child_node,child_node_b1)
    child_node=User(name="B1_3")
    tm.add_node(child_node,child_node_b1)

    #增加另一棵树
    root_node = User(name="root2")
    root_node.tree_id=1
    tm.add_node(root_node)

    child_node_a=User(name="2-A")
    tm.add_node(child_node_a,root_node)

    child_node_b=User(name="2-B")
    tm.add_node(child_node_b,root_node)

    child_node_b=User(name="2-C")
    tm.add_node(child_node_b,root_node)

elif ACTION==1:#删除节点
    ref_node = session.query(User).filter(User.name == "B").one()
    tm.del_node(ref_node)
elif ACTION==2:#删除全部
    ref_node = session.query(User).filter(User.name == "root1").one()
    tm.del_node(ref_node)
elif ACTION==3:#增加第一个子项目
    ref_node = session.query(User).filter(User.name == "B").one()
    for i in range(2,5):
        new_child=User(name="B_first_child_%s" % i)
        tm.add_node(new_child,ref_node,pos=1)
elif ACTION==4:#增加为下一节点
    ref_node = session.query(User).filter(User.name == "B1").one()
    for i in range(2,5):
        new_child=User(name="B1_next_%s" % i)
        tm.add_node(new_child,ref_node,pos=2)
elif ACTION==5:#增加为上一节点
    ref_node = session.query(User).filter(User.name == "B").one()
    for i in range(2,3):
        new_child=User(name="B_pre_%s" % i)
        tm.add_node(new_child,ref_node,pos=3)
elif ACTION==6:#移动节点到最后一个子节点
    ref_node = session.query(User).filter(User.name == "A").one()
    move_node = session.query(User).filter(User.name == "B2").one()
    #将B节点移动到A节点下
    tm.move_node(move_node,ref_node,pos=0)
elif ACTION==7:#移动节点到第一个子节点
    ref_node = session.query(User).filter(User.name == "A").one()
    move_node = session.query(User).filter(User.name == "B2").one()
    #将B节点移动到A节点下
    tm.move_node(move_node,ref_node,pos=1)
elif ACTION==8:#移动节点下一节点
    ref_node = session.query(User).filter(User.name == "C").one()
    move_node = session.query(User).filter(User.name == "B1").one()
    tm.move_node(move_node,ref_node,pos=2)
    session.commit()
    tm.move_node(move_node,ref_node,pos=3)
    session.commit()

elif ACTION==9:#将B1树从Root1移到Root2树下
    ref_node = session.query(User).filter(User.name == "root2").one()
    move_node = session.query(User).filter(User.name == "B1").one()
    tm.move_node(move_node,ref_node,pos=0)
elif ACTION==10:

    #Base.metadata.create_all(engine)
    root_node = User(name="root1")
    root_node.set_root()

    child_node_a=User(name="A")
    root_node.add_child(child_node_a)

    child_node_b=User(name="B")
    root_node.add_child(child_node_b)


session.commit()
session.close()





   # def _get_tree_fileds(self):
   #      """
   #      取得返回树节点时的字段列表
   #      :return:
   #      """
   #      if hasattr(self._model_class,"__tree_fields__"):
   #          fileds=self._model_class.__tree_fields__
   #      else:
   #          fileds=self._model_class
   #  @property
   #  def tree_fields(self):
   #      """
   #      返回节点时的字段名称列表，必须是可迭代的,
   #      如tm.node_fields=["A","B","C"]
   #      """
   #      if self._tree_fields is None:
   #          self._tree_fields=[self.get_primary_field().name,"tree_id","tree_left","tree_right","tree_level"]
   #          if hasattr(self._model_class,"__tree_fields__") and isinstance(self._model_class.__tree_fields__,list):
   #              self._tree_fields.extend(self._model_class.__tree_fields__)
   #      return self._tree_fields
   #
   #  @tree_fields.setter
   #  def tree_fields(self,value):
   #      assert isinstance(value,list),u'必须是列表类型'
   #      value.extend([self.get_primary_field().name,"tree_id","tree_left","tree_right","tree_level"])
   #      self._tree_fields=value
   #
   #  def _get_return_fields(self):
   #      """
   #          取得应该返回的字段列表
   #          如果没有指定__tree_fields__，则返回全部
   #      """
   #      if hasattr(self._model_class,"__tree_fields__"):
   #          if self._model_class.__tree_fields__=="*":
   #              return self._model_class
   #          else:
   #              return self.tree_fields
   #      else:
   #          return self._model_class
            #if pos==TREE_NODE_POSITION.LastChild:#增加为最后一个子节点
                # #更新节点left,right值
                # session.query(cls).filter(and_(cls.tree_right>=ref_right,cls.__dict__[cls.__tree_key__]==ref_tree_id)).update({cls.tree_right:cls.tree_right+2})
                # session.query(cls).filter(and_(cls.tree_left>=ref_right,cls.__dict__[cls.__tree_key__]==ref_tree_id)).update({cls.tree_left:cls.tree_left+2})
                # #增加新节点
                # nodes.tree_left=ref_right
                # nodes.tree_right=ref_right+1
                # nodes.tree_level=ref_level+1
           # elif pos==TREE_NODE_POSITION.FirstChild:#增加为第一个子节点
                #
                # #更新节点left,right值
                # session.query(cls).filter(and_(cls.tree_left>ref_left,cls.__dict__[cls.__tree_key__]==ref_tree_id)).update({cls.tree_left:cls.tree_left+2})
                # session.query(cls).filter(and_(cls.tree_right>=ref_left+1,cls.__dict__[cls.__tree_key__]==ref_tree_id)).update({cls.tree_right:cls.tree_right+2})
                #
                #
                # nodes.tree_left=ref_left+1
                # nodes.tree_right=ref_left+2
                # nodes.tree_level=ref_level+1
            #elif pos==TREE_NODE_POSITION.NextSibling:#增加为下一个兄弟节点
                # session.query(cls).filter(and_(cls.tree_left>ref_right,cls.__dict__[cls.__tree_key__]==ref_tree_id)).update({cls.tree_left:cls.tree_left+2})
                # session.query(cls).filter(and_(cls.tree_right>ref_right+1,cls.__dict__[cls.__tree_key__]==ref_tree_id)).update({cls.tree_right:cls.tree_right+2})
                # nodes.tree_left=ref_right+1
                # nodes.tree_right=ref_right+2
                # nodes.tree_level=ref_level
            #elif pos==TREE_NODE_POSITION.PreviousSibling:#增加为上一个兄弟节点
                # session.query(cls).filter(and_(cls.tree_left>=ref_left,cls.__dict__[cls.__tree_key__]==ref_tree_id)).update({cls.tree_left:cls.tree_left+2})
                # session.query(cls).filter(and_(cls.tree_right>=ref_left+1,cls.__dict__[cls.__tree_key__]==ref_tree_id)).update({cls.tree_right:cls.tree_right+2})
                # nodes.tree_left=ref_left
                # nodes.tree_right=ref_left+1
                # nodes.tree_level=ref_level