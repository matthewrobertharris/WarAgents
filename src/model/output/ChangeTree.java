package model.output;

import model.Agent;
import model.Map;
import model.tree.Tree;

public class ChangeTree extends Action {

	private String tree;
	public ChangeTree(String tree) {
		setTree(tree);
	}
	
	public String getTree() {
		return tree;
	}

	public void setTree(String tree) {
		this.tree = tree;
	}

	@Override
	public boolean action(Agent agent, Map map) {
		for(Tree tree : agent.getPlayer().getTrees()) {
			if(tree.getName().equals(getTree())) {
				agent.setTree(tree);
				return true;
			}
		}
		return false;
	}
	
	public String toString() {
		String output = getActivity().toString();
		return output;
	}
	
	@Override
	public Activity getActivity() {
		return Activity.CHANGE_TREE;
	}

}
