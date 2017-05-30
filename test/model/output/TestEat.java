package model.output;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import org.junit.After;
import org.junit.Test;

import junit.framework.TestCase;
import main.Game;
import model.Agent;
import model.Map;
import model.output.Action.Activity;
import readers.ActionReaderImpl;
import readers.CriteriaReaderImpl;
import readers.GameReader;
import readers.GameReaderImpl;
import readers.InputReaderImpl;
import readers.MapReaderImpl;
import readers.ModeReaderImpl;
import readers.PlantReaderImpl;
import readers.PlayerReaderImpl;
import readers.PositionReaderImpl;
import readers.TreeReaderImpl;

public class TestEat extends TestCase {

	private GameReader gameReader;
	private final ByteArrayOutputStream outContent = new ByteArrayOutputStream();

	@Override
	protected void setUp() {
		gameReader = new GameReaderImpl(new MapReaderImpl(new PlantReaderImpl(),
				new PlayerReaderImpl(new TreeReaderImpl(new ActionReaderImpl(new PositionReaderImpl()), new InputReaderImpl(new PositionReaderImpl()))),
				new CriteriaReaderImpl(new ActionReaderImpl(new PositionReaderImpl())), new ModeReaderImpl()));
		System.setOut(new PrintStream(outContent));
	}
	
	@After
	public void cleanUpStreams() {
	    System.setOut(null);
	}

	/**
	 * http://stackoverflow.com/questions/1119385/junit-test-for-system-out-println
	 */
	@Test
	public void testEat_Success_AllFood() {
		String file = "resources\\test\\outputMaps\\test_eat_success_allFood.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int food = map.getTile(agent.getCurrentPos()).getFood();
		int prevHealth = 50;
		agent.setHealth(prevHealth);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.EAT);
		assertTrue(agent.getHealth() == (prevHealth + food));
		assertTrue(map.getTile(agent.getCurrentPos()).getFood() == 0);
	}
	
	@Test
	public void testEat_Success_PartialFood() {
		String file = "resources\\test\\outputMaps\\test_eat_success_partialFood.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int food = map.getTile(agent.getCurrentPos()).getFood();
		int prevHealth = 95;
		agent.setHealth(prevHealth);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.EAT);
		assertTrue(agent.getHealth() == agent.getMaxHealth());
		assertTrue(map.getTile(agent.getCurrentPos()).getFood() == (food - (agent.getMaxHealth() - prevHealth)));
	}
	
	@Test
	public void testEat_Fail_NoFood() {
		String file = "resources\\test\\outputMaps\\test_eat_fail_noFood.map";
		String error = "Cannot EAT because map has no food\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int prevHealth = 95;
		agent.setHealth(prevHealth);
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.EAT);
		assertTrue(agent.getHealth() == prevHealth);
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testEat_Fail_MaxHealth() {
		String file = "resources\\test\\outputMaps\\test_eat_fail_maxHealth.map";
		String error = "Cannot EAT because agent is at full health\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.EAT);
		assertTrue(agent.getHealth() == agent.getMaxHealth());
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void test_ToString() {
		Eat output = new Eat();
		String strOutput = "EAT";
		assertTrue(output.toString().equals(strOutput));
	}
	
}
